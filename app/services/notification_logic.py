from app.services.fcm_service import send_notification
from app.models import User, DeviceToken


def _get_tokens(db, user_id):
    """Helper: get FCM token list for a user"""
    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
    return [t.token for t in tokens]


def _get_name(db, user_id):
    """Helper: get user name"""
    user = db.query(User).filter(User.id == user_id).first()
    return f"{user.first_name} {user.last_name}" if user else "Someone"


# ─── RIDE REQUEST FLOW ──────────────────────────────────────────

def notify_driver_new_request(db, driver_id, passenger_id):
    """Passenger requested a ride → notify driver"""
    tokens = _get_tokens(db, driver_id)
    name = _get_name(db, passenger_id)
    send_notification(tokens,
        title="New Ride Request",
        body=f"{name} has requested a seat in your ride"
    )


def notify_passenger_request_accepted(db, passenger_id, driver_id):
    """Driver accepted request → notify passenger"""
    tokens = _get_tokens(db, passenger_id)
    name = _get_name(db, driver_id)
    send_notification(tokens,
        title="Request Accepted ",
        body=f"{name} accepted your ride request. Get ready!"
    )


def notify_passenger_request_rejected(db, passenger_id, driver_id):
    """Driver rejected request → notify passenger"""
    tokens = _get_tokens(db, passenger_id)
    name = _get_name(db, driver_id)
    send_notification(tokens,
        title="Request Rejected ",
        body=f"{name} could not accommodate your request. Try another ride."
    )


def notify_driver_request_cancelled(db, driver_id, passenger_id):
    """Passenger cancelled their request → notify driver"""
    tokens = _get_tokens(db, driver_id)
    name = _get_name(db, passenger_id)
    send_notification(tokens,
        title="Request Cancelled",
        body=f"{name} cancelled their ride request"
    )


# ─── RIDE LIFECYCLE ─────────────────────────────────────────────

def notify_passengers_ride_started(db, passenger_ids, driver_id):
    """Driver started the ride → notify all accepted passengers"""
    driver_name = _get_name(db, driver_id)
    for pid in passenger_ids:
        tokens = _get_tokens(db, pid)
        send_notification(tokens,
            title="Ride Started ",
            body=f"{driver_name} has started the ride. Please be at your pickup point!"
        )


def notify_passenger_picked_up(db, passenger_id, driver_id):
    """Driver marked passenger as picked up → notify that passenger"""
    tokens = _get_tokens(db, passenger_id)
    driver_name = _get_name(db, driver_id)
    send_notification(tokens,
        title="You're On Board! ",
        body=f"{driver_name} has marked you as picked up. Enjoy the ride!"
    )


def notify_passengers_ride_completed(db, passenger_ids, driver_id):
    """Ride completed → notify all passengers"""
    driver_name = _get_name(db, driver_id)
    for pid in passenger_ids:
        tokens = _get_tokens(db, pid)
        send_notification(tokens,
            title="Ride Completed ",
            body=f"Your ride with {driver_name} is complete. Hope you had a great trip!"
        )


def notify_passengers_ride_cancelled(db, passenger_ids, driver_id):
    """Driver cancelled the ride → notify all affected passengers"""
    driver_name = _get_name(db, driver_id)
    for pid in passenger_ids:
        tokens = _get_tokens(db, pid)
        send_notification(tokens,
            title="Ride Cancelled ",
            body=f"{driver_name} has cancelled the ride. Please look for another ride."
        )