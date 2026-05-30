# rule-based pattern recognition is used
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from collections import Counter
from app.models import RideRequest, Ride, User, DeviceToken
from app.services.fcm_service import send_notification
import math


# Harvesian Distance
def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


#Pattern history analyze
def get_passenger_pattern(db: Session, passenger_id: int) -> dict | None:

    since = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)

    requests = (
        db.query(RideRequest)
        .join(Ride, Ride.id == RideRequest.ride_id)
        .filter(
            RideRequest.passenger_id == passenger_id,
            RideRequest.status == "completed",
            Ride.departure_time >= since,
        )
        .all()
    )

    if not requests:
        return None

    # collect (weekday, hour, pickup_lat, pickup_lng) per ride
    entries = []
    for req in requests:
        ride = req.ride
        dep = ride.departure_time
        if dep.tzinfo is None:
            dep = dep.replace(tzinfo=timezone.utc)

        entries.append({
            "weekday": dep.weekday(),       # 0=Mon … 6=Sun
            "hour":    dep.hour,
            "pickup_lat": req.pickup_lat or ride.from_lat,
            "pickup_lng": req.pickup_lng or ride.from_lng,
            "to_lat":  ride.to_lat,
            "to_lng":  ride.to_lng,
            "gender_filter": ride.gender_filter,
        })

    if not entries:
        return None

    # most common weekday
    weekday = Counter(e["weekday"] for e in entries).most_common(1)[0][0]

    # filter to that weekday only
    day_entries = [e for e in entries if e["weekday"] == weekday]

    # most common hour (rounded)
    hour = Counter(e["hour"] for e in day_entries).most_common(1)[0][0]

    # average pickup location
    avg_pickup_lat = sum(e["pickup_lat"] for e in day_entries) / len(day_entries)
    avg_pickup_lng = sum(e["pickup_lng"] for e in day_entries) / len(day_entries)

    # average destination
    avg_to_lat = sum(e["to_lat"] for e in day_entries) / len(day_entries)
    avg_to_lng = sum(e["to_lng"] for e in day_entries) / len(day_entries)

    # passenger gender (for gender_filter matching)
    passenger = db.query(User).filter(User.id == passenger_id).first()
    gender = passenger.gender if passenger else "any"

    return {
        "passenger_id":  passenger_id,
        "weekday":       weekday,           
        "hour":          hour,               
        "avg_pickup_lat": avg_pickup_lat,
        "avg_pickup_lng": avg_pickup_lng,
        "avg_to_lat":    avg_to_lat,
        "avg_to_lng":    avg_to_lng,
        "gender":        gender,
        "ride_count":    len(day_entries),  
    }


#Find matching future rides
def find_matching_rides(db: Session, pattern: dict) -> list:
    now = datetime.now(timezone.utc)
    results = []

    for days_ahead in range(1, 8):
        target_date = (now + timedelta(days=days_ahead)).date()
        if target_date.weekday() != pattern["weekday"]:
            continue

        window_start = datetime(
          target_date.year, target_date.month, target_date.day,
          max(pattern["hour"] - 1, 0), 0, 0  
        )
        window_end = datetime(
          target_date.year, target_date.month, target_date.day,
          min(pattern["hour"] + 1, 23), 59, 59  
        )

        rides = (
            db.query(Ride)
            .filter(
                Ride.status == "active",
                Ride.departure_time >= window_start.replace(tzinfo=None),
                Ride.departure_time <= window_end.replace(tzinfo=None),
                Ride.seats_available > 0,
                Ride.driver_id != pattern["passenger_id"],
            )
            .all()
        )

        results.extend(rides)
        break 

    already_requested = {
        rr.ride_id
        for rr in db.query(RideRequest).filter(
            RideRequest.passenger_id == pattern["passenger_id"],
            RideRequest.status.in_(["pending", "accepted", "completed"]),
        ).all()
    }

    matched = []
    for ride in results:
        if ride.id in already_requested:
            continue
        pickup_dist = haversine(
            pattern["avg_pickup_lat"], pattern["avg_pickup_lng"],
            ride.from_lat, ride.from_lng
        )
        if pickup_dist > 7:
            continue
        if (ride.gender_filter != "any" and
                ride.gender_filter != pattern["gender"]):
            continue
        matched.append(ride)

    return matched  

#Send Recommendation notification
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday",
                 "Thursday", "Friday", "Saturday", "Sunday"]

def send_recommendation_notification(db: Session, passenger_id: int, rides: list):
    tokens = [
        t.token for t in
        db.query(DeviceToken).filter(DeviceToken.user_id == passenger_id).all()
    ]

    if not tokens:
        return  

    for ride in rides:
        driver = db.query(User).filter(User.id == ride.driver_id).first()
        driver_name = f"{driver.first_name} {driver.last_name}" if driver else "A driver"

        dep = ride.departure_time
        if dep.tzinfo is None:
            dep = dep.replace(tzinfo=timezone.utc)
        time_str = dep.strftime("%I:%M %p")  # e.g. 09:45 AM

        send_notification(
            tokens,
            title="Ride Recommendation 🚗",
            body=(
                f"{driver_name} is leaving from your area at {time_str} "
                f"on {WEEKDAY_NAMES[dep.weekday()]}. Want to join?"
            ),
        )

def run_recommendations(db: Session) -> list:

    passengers = db.query(User).filter(User.is_passenger == True).all()

    results = []
    for passenger in passengers:
        pattern = get_passenger_pattern(db, passenger.id)
        if not pattern:
            continue  

        matched_rides = find_matching_rides(db, pattern)
        if not matched_rides:
            continue

        send_recommendation_notification(db, passenger.id, matched_rides)

        results.append({
            "passenger_id":   passenger.id,
            "passenger_name": f"{passenger.first_name} {passenger.last_name}",
            "pattern": {
                "weekday": WEEKDAY_NAMES[pattern["weekday"]],
                "hour":    pattern["hour"],
                "rides_in_history": pattern["ride_count"],
            },
            "recommended_rides": [
                {
                    "ride_id":     r.id,
                    "driver_id":   r.driver_id,
                    "from":        r.from_address,
                    "to":          r.to_address,
                    "departure":   r.departure_time.isoformat(),
                    "fare":        r.fare_per_seat,
                    "seats_left":  r.seats_available,
                }
                for r in matched_rides
            ],
        })

    return results
