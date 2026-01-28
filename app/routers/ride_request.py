from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
from ..utils import haversine, within_time_window
from datetime import datetime

router = APIRouter(prefix="/ride_requests", tags=["Ride Requests"])

#Passenger requests a ride (booking)
@router.post("/", response_model=schemas.RideRequestOut)
def request_ride(
    data: schemas.RideRequestCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(oauth2.get_current_user)
):
    if current_user.role != "passenger":
        raise HTTPException(status_code=403, detail="Only passengers can request rides")

    ride = db.query(models.Ride).filter(models.Ride.id == data.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # Check if passenger already booked
    existing = db.query(models.RideRequest).filter(
        models.RideRequest.ride_id == ride.id,
        models.RideRequest.passenger_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already booked this ride")

    # Auto accept request
    distance = haversine(ride.from_lat, ride.from_lng, ride.from_lat, ride.from_lng)
    status = "accepted"

    ride_request = models.RideRequest(
        ride_id=ride.id,
        passenger_id=current_user.id,
        status=status,
        distance_from_route=distance
    )

    db.add(ride_request)

    #Correct seat decrease logic
    if ride.vehicle.mode_of_transport == "car" and ride.seats_available > 0:
        ride.seats_available -= 1
        # Optional: mark ride as full instead of deleting
        if ride.seats_available == 0:
            ride.status = "full"  # DB me ride record still rahega

    db.commit()
    db.refresh(ride_request)
    return ride_request

# Search available rides (passenger filters)
@router.get("/search", response_model=list[schemas.RideOut])
def search_rides(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    target_time: datetime,
    mode_of_transport: str = None,  # new: 'bike' or 'car'
    ac: bool = None,
    gender: str = None,
    db: Session = Depends(database.get_db),
    current_user=Depends(oauth2.get_current_user)
):
    if current_user.role != "passenger":
        raise HTTPException(status_code=403, detail="Only passengers can search rides")

    rides = db.query(models.Ride).filter(models.Ride.departure_time > datetime.utcnow()).all()
    results = []

    for ride in rides:
        pickup_distance = haversine(from_lat, from_lng, ride.from_lat, ride.from_lng)
        drop_distance = haversine(to_lat, to_lng, ride.to_lat, ride.to_lng)
        if pickup_distance > 7 or drop_distance > 7:
            continue

        if not within_time_window(ride.departure_time, target_time, margin_minutes=20):
            continue

        # Filter by mode_of_transport if passenger selected
        if mode_of_transport is not None and ride.vehicle.mode_of_transport != mode_of_transport:
            continue

        # AC filter only for car
        if ride.vehicle.mode_of_transport == "car" and ac is not None and ride.ac != ac:
            continue

        # Gender filter for both bike & car
        if gender is not None and ride.gender_filter != "any" and ride.gender_filter != gender:
            continue

        results.append(ride)

    return results

