#passanger request seat, driver accept/reject ride, passanger can cancel request, passanger search rides

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from .. import models, schemas, database
from ..utils import haversine, within_time_window
from typing import Optional
from ..dependencies import require_driver, require_passenger
from ..services.notification_logic import (
    notify_driver_new_request,
    notify_passenger_request_accepted,
    notify_passenger_request_rejected,
    notify_driver_request_cancelled,
)

router = APIRouter(prefix="/ride_requests", tags=["Ride Requests"])


@router.post("/", response_model=schemas.RideRequestOut, status_code=status.HTTP_201_CREATED)
def request_ride(
    data: schemas.RideRequestCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(require_passenger)
):
    ride = db.query(models.Ride).filter(models.Ride.id == data.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    if ride.driver_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot request your own ride")

    now = datetime.now(timezone.utc)
    dep = ride.departure_time
    if dep.tzinfo is None:
        dep = dep.replace(tzinfo=timezone.utc)

    if ride.status != "active":
        raise HTTPException(status_code=400, detail="Ride is not available")

    if dep <= now:
        raise HTTPException(status_code=400, detail="Ride departure time has passed")

    if ride.seats_available <= 0:
        ride.status = "full"
        db.commit()
        raise HTTPException(status_code=400, detail="Ride is full")

    existing = db.query(models.RideRequest).filter(
        models.RideRequest.ride_id == ride.id,
        models.RideRequest.passenger_id == current_user.id,
        models.RideRequest.status.in_(["pending", "accepted"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active request for this ride")

    ride_request = models.RideRequest(
        ride_id=ride.id,
        passenger_id=current_user.id,
        status="pending",
        distance_from_route=0.0,
        pickup_lat=data.pickup_lat,
        pickup_lng=data.pickup_lng
    )

    db.add(ride_request)
    db.commit()
    db.refresh(ride_request)

    try:
        notify_driver_new_request(db, driver_id=ride.driver_id, passenger_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return ride_request


@router.post("/{request_id}/accept", response_model=schemas.RideRequestOut)
def accept_request(
    request_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(require_driver)
):
    req = db.query(models.RideRequest).filter(models.RideRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    ride = db.query(models.Ride).filter(models.Ride.id == req.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    if ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage requests for your own ride")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot accept request with status '{req.status}'")

    if ride.status != "active":
        raise HTTPException(status_code=400, detail="Ride is not available")

    if ride.seats_available <= 0:
        ride.status = "full"
        db.commit()
        raise HTTPException(status_code=400, detail="Ride is full")

    req.status = "accepted"
    ride.seats_available -= 1

    if ride.seats_available == 0:
        ride.status = "full"

    db.commit()
    db.refresh(req)

    try:
        notify_passenger_request_accepted(db, passenger_id=req.passenger_id, driver_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return req


@router.post("/{request_id}/reject", response_model=schemas.RideRequestOut)
def reject_request(
    request_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(require_driver)
):
    req = db.query(models.RideRequest).filter(models.RideRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    ride = db.query(models.Ride).filter(models.Ride.id == req.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    if ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage requests for your own ride")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject request with status '{req.status}'")

    req.status = "rejected"
    db.commit()
    db.refresh(req)

    try:
        notify_passenger_request_rejected(db, passenger_id=req.passenger_id, driver_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return req


@router.post("/{request_id}/cancel", response_model=schemas.RideRequestOut)
def cancel_request(
    request_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(require_passenger)
):
    req = db.query(models.RideRequest).filter(models.RideRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.passenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own request")

    if req.status not in ["pending", "accepted"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel request with status '{req.status}'")

    ride = db.query(models.Ride).filter(models.Ride.id == req.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    was_accepted = (req.status == "accepted")
    req.status = "cancelled_by_passenger"

    if was_accepted:
        ride.seats_available += 1
        if ride.status == "full":
            ride.status = "active"

    db.commit()
    db.refresh(req)

    try:
        notify_driver_request_cancelled(db, driver_id=ride.driver_id, passenger_id=current_user.id)
    except Exception as e:
        print(f"Notification failed: {e}")

    return req


@router.get("/search", response_model=list[schemas.RideOut])
def search_rides(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    target_time: datetime,
    mode_of_transport: Optional[str] = None,
    ac: Optional[bool] = None,
    gender: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user=Depends(require_passenger)
):
    now = datetime.now(timezone.utc)
    rides = db.query(models.Ride).filter(
        models.Ride.departure_time > now,
        models.Ride.status == "active",
        models.Ride.seats_available > 0
    ).all()

    results = []
    for ride in rides:
        pickup_distance = haversine(from_lat, from_lng, ride.from_lat, ride.from_lng)
        drop_distance = haversine(to_lat, to_lng, ride.to_lat, ride.to_lng)

        if pickup_distance > 7 or drop_distance > 7:
            continue

        if not within_time_window(ride.departure_time, target_time, margin_minutes=15):
            continue

        if mode_of_transport is not None and ride.vehicle.mode_of_transport != mode_of_transport:
            continue

        if ride.vehicle.mode_of_transport == "car" and ac is not None and ride.ac != ac:
            continue

        if gender is not None and ride.gender_filter != "any" and ride.gender_filter != gender:
            continue

        results.append(ride)

    return results