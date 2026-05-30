from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal, get_db
from ..models import RideLocation, Ride, RideRequest
from ..dependencies import require_driver
from ..utils import haversine
from ..services.location_service import location_manager, get_eta
from ..services.notification_logic import (
    notify_passengers_ride_started,
    notify_passenger_picked_up,
)
from .. import oauth2
import json

router = APIRouter(prefix="/location", tags=["Location"])


# START RIDE
@router.post("/{ride_id}/start")
def start_ride(ride_id: int, db=Depends(get_db), current_user=Depends(require_driver)):

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(404, "Ride not found")

    if ride.driver_id != current_user.id:
        raise HTTPException(403, "Not your ride")

    ride.status = "ongoing"
    db.commit()

    return {
        "message": "Ride started",
        "ws_url": f"/location/ws/{ride_id}"
    }

# WEBSOCKET LIVE LOCATION
@router.websocket("/ws/{ride_id}")
async def location_websocket(websocket: WebSocket, ride_id: int):
    print("WEBSOCKET CONNECTED")
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        token_data = oauth2.verify_access_token(
            token,
            HTTPException(status_code=403, detail="Invalid token")
        )
        driver_id = token_data.id

    except Exception as e:
        print("AUTH ERROR:", e)
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    await location_manager.connect(websocket, ride_id)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            if data.get("type") != "location":
                continue

            lat = data["lat"]
            lng = data["lng"]
            print("MESSAGE RECEIVED:", raw_data)

            # SAVE LOCATION
            db.add(RideLocation(
                ride_id=ride_id,
                driver_id=driver_id,
                latitude=lat,
                longitude=lng
            ))
            db.commit()

            # NEXT STOP
            next_stop = get_next_pickup(ride_id, db, lat, lng)
            passangers = db.query(RideRequest).filter(
                   RideRequest.ride_id == ride_id,
                   RideRequest.status == "accepted",
                   RideRequest.pickup_lat.isnot(None)
            ).all()
            print("pending psg:", passangers)


            # ETA
            eta_seconds = None
            eta_minutes = None

            if next_stop:
                eta_seconds = await get_eta(
                    lat, lng,
                    next_stop["lat"],
                    next_stop["lng"]
                )

            if eta_seconds is not None:
             eta_minutes = max(1, int(eta_seconds / 60)) if eta_seconds > 0 else 0

            # BROADCAST
            await location_manager.broadcast_location(ride_id, {
                "type": "driver_location",
                "ride_id": ride_id,
                "lat": lat,
                "lng": lng,
                "eta_seconds": eta_seconds,
                "eta_minutes": eta_minutes,
                "next_stop": next_stop
            })

    except WebSocketDisconnect:
        location_manager.disconnect(websocket, ride_id)

    except Exception as e:
        print("WS ERROR:", e)

    finally:
        db.close()


#next pickup
def get_next_pickup(ride_id: int, db: Session, driver_lat: float, driver_lng: float):

    passengers = db.query(RideRequest).filter(
        RideRequest.ride_id == ride_id,
        RideRequest.status == "accepted",
        RideRequest.pickup_lat.isnot(None)
    ).all()

    if not passengers:
        return None

    nearest = min(
        passengers,
        key=lambda r: haversine(driver_lat, driver_lng, r.pickup_lat, r.pickup_lng)
    )

    return {
        "passenger_id": nearest.passenger_id,
        "lat": nearest.pickup_lat,
        "lng": nearest.pickup_lng
    }