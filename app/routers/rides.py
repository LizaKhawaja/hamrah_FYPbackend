#Driver ride post and view all posted rides
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..models import Ride, User, Vehicle
from ..schemas import RideOut, RideCreate
from ..dependencies import require_driver  

router = APIRouter(prefix="/rides", tags=["Rides"])


@router.post("/", response_model=RideOut, status_code=status.HTTP_201_CREATED)
def post_ride(
    ride: RideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),  
):

    # vehicle must belong to driver
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == ride.vehicle_id,
        Vehicle.user_id == current_user.id
    ).first()
    if not vehicle:
        raise HTTPException(status_code=400, detail="Invalid vehicle selection")

    #  departure must be in the future
    now = datetime.now(timezone.utc)
    dep = ride.departure_time
    if dep.tzinfo is None:  #if timezone not provided assume utc (to make comparable)
        dep = dep.replace(tzinfo=timezone.utc)
    if dep <= now:
        raise HTTPException(status_code=400, detail="departure_time must be in the future")

    # Bike: seats/ac MUST NOT be provided (frontend will not show only backend check)
    if vehicle.mode_of_transport == "bike":  #postman will show error
        if ride.seats_available is not None:
            raise HTTPException(status_code=400, detail="seats_available is not allowed for bike rides")
        if ride.ac is not None:
            raise HTTPException(status_code=400, detail="ac is not allowed for bike rides")
        seats = 1
        ac_value = None

    # Car: seats and ac mandatory
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


#driver can view all requests (completed, active)
@router.get("/my", response_model=list[RideOut])
def my_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),  
):
    return db.query(Ride).filter(Ride.driver_id == current_user.id).all()