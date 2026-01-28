from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from ..models import Ride, RideRequest, User, Vehicle
from ..schemas import RideOut, RideCreate
from ..oauth2 import get_current_user

router = APIRouter(prefix="/rides", tags=["Rides"])

#Driver posts a ride
@router.post("/", response_model=RideOut)
def post_ride(
    ride: RideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "driver":
        raise HTTPException(403, "Only drivers can post rides")

    # 🔐 check vehicle belongs to driver
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == ride.vehicle_id,
        Vehicle.user_id == current_user.id
    ).first()

    if not vehicle:
        raise HTTPException(400, "Invalid vehicle selection")

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
        seats_available=ride.seats_available,
        ac=ride.ac if vehicle.mode_of_transport == "car" else None,
        fare_per_seat=ride.fare_per_seat,
        gender_filter=ride.gender_filter
    )

    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return new_ride

#List rides posted by driver
@router.get("/my", response_model=list[RideOut])
def my_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "driver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only drivers can view rides")

    return db.query(Ride).filter(Ride.driver_id == current_user.id).all()




# #Cancel ride (driver can cancel entire ride)
# @router.delete("/{ride_id}", response_model=dict)
# def cancel_ride(
#     ride_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     ride = db.query(Ride).filter(Ride.id == ride_id, Ride.driver_id == current_user.id).first()
#     if not ride:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

#     db.delete(ride)
#     db.commit()
#     return {"detail": "Ride canceled successfully"}

# #Remove a specific passenger
# @router.delete("/{ride_id}/passengers/{request_id}", response_model=dict)
# def reject_passenger(
#     ride_id: int,
#     request_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     #Driver check
#     if current_user.role != "driver":
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only drivers can cancel passengers")

#     #Ride ownership check
#     ride = db.query(Ride).filter(
#         Ride.id == ride_id,
#         Ride.driver_id == current_user.id
#     ).first()
#     if not ride:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

#     #Passenger request check
#     request = db.query(RideRequest).filter(
#         RideRequest.id == request_id,
#         RideRequest.ride_id == ride_id,
#         RideRequest.status == "accepted"
#     ).first()
#     if not request:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passenger not found in this ride")

#     #Cancel passenger
#     request.status = "cancelled_by_driver"
#     ride.seats_available += 1  # seat wapas

#     db.commit()
#     return {"detail": "Passenger removed from ride"}
