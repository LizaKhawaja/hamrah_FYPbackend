from app.services.fcm_service import send_notification
from app.models import User
from app.models import DeviceToken


def notify_driver_new_request(db, driver_id, passenger_id):

    driver = db.query(User).filter(User.id == driver_id).first()
    passenger = db.query(User).filter(User.id == passenger_id).first()

    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == driver_id).all()
    token_list = [t.token for t in tokens]

    title = "New Ride Request 🚗"
    body = f"{passenger.name} requested a ride"

    send_notification(token_list, title, body)