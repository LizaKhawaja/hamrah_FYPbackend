#Driver ride offer, driver can view all his rides, driver complete ride and driver can cancel ride
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..models import Ride, User, Vehicle, RideRequest
from ..schemas import RideOut, RideCreate
from ..dependencies import require_driver
from ..services.notification_logic import (
    notify_passengers_ride_completed,
    notify_passengers_ride_cancelled,
)

router = APIRouter(prefix="/rides", tags=["Rides"])


@router.post("/", response_model=RideOut, status_code=status.HTTP_201_CREATED)
def post_ride(
    ride: RideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == ride.vehicle_id,
        Vehicle.user_id == current_user.id
    ).first()
    if not vehicle:
        raise HTTPException(status_code=400, detail="Invalid vehicle selection")

    now = datetime.now(timezone.utc)
    dep = ride.departure_time
    if dep.tzinfo is None:
        dep = dep.replace(tzinfo=timezone.utc)
    if dep <= now:
        raise HTTPException(status_code=400, detail="departure_time must be in the future")

    if vehicle.mode_of_transport == "bike":
        if ride.seats_available is not None:
            raise HTTPException(status_code=400, detail="seats_available is not allowed for bike rides")
        if ride.ac is not None:
            raise HTTPException(status_code=400, detail="ac is not allowed for bike rides")
        seats = 1
        ac_value = None

    elif vehicle.mode_of_transport == "car":
        if ride.seats_available is None or ride.seats_available < 1:
            raise HTTPException(status_code=400, detail="seats_available is required for car rides and must be >= 1")
        if ride.ac is None:
            raise HTTPException(status_code=400, detail="ac is required for car rides (true/false)")
        seats = ride.seats_available
        ac_value = ride.ac

    else:
        raise HTTPException(status_code=400, detail="Invalid mode_of_transport on vehicle")

    new_ride = Ride(
        driver_id=current_user.id,
        vehicle_id=vehicle.id,
        from_address=ride.from_address,
        from_lat=ride.from_lat,
        from_lng=ride.from_lng,
        to_address=ride.to_address,
        to_lat=ride.to_lat,
        to_lng=ride.to_lng,
        departure_time=ride.departure_time,
        seats_available=seats,
        ac=ac_value,
        fare_per_seat=ride.fare_per_seat,
        gender_filter=ride.gender_filter,
        status="active",
    )

    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return new_ride


@router.get("/my", response_model=list[RideOut])
def my_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    return db.query(Ride).filter(Ride.driver_id == current_user.id).all()


@router.post("/{ride_id}/complete")
def complete_ride(
    ride_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_driver)
):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    if ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the driver can complete this ride")

    if ride.status != "ongoing":
        raise HTTPException(status_code=400, detail=f"Ride cannot be completed — current status is {ride.status}")

    not_picked = db.query(RideRequest).filter(
        RideRequest.ride_id == ride_id,
        RideRequest.status == "accepted"
    ).count()

    if not_picked > 0:
        raise HTTPException(
            status_code=400,
            detail=f"{not_picked} passenger(s) have not been picked up yet"
        )

    ride.status = "completed"

    db.query(RideRequest).filter(
        RideRequest.ride_id == ride_id,
        RideRequest.status == "picked_up"
    ).update({"status": "completed"})

    db.commit()

    # fetch passengers AFTER commit
    completed_requests = db.query(RideRequest).filter(
        RideRequest.ride_id == ride_id,
        RideRequest.status == "completed"
    ).all()
    passenger_ids = [r.passenger_id for r in completed_requests]

    try:
        notify_passengers_ride_completed(db, passenger_ids=passenger_ids, driver_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return {"message": "Ride completed successfully", "ride_id": ride_id}


@router.post("/{ride_id}/cancel")
def cancel_ride(
    ride_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_driver)
):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    if ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the driver can cancel this ride")

    if ride.status in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Ride already {ride.status}")

    # fetch BEFORE commit
    affected = db.query(RideRequest).filter(
        RideRequest.ride_id == ride_id,
        RideRequest.status.in_(["pending", "accepted"])
    ).all()
    passenger_ids = [r.passenger_id for r in affected]

    ride.status = "cancelled"
    for r in affected:
        r.status = "cancelled_by_driver"
    db.commit()

    try:
        notify_passengers_ride_cancelled(db, passenger_ids=passenger_ids, driver_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return {"message": "Ride cancelled", "ride_id": ride_id}