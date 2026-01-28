import hashlib
import secrets
import random 
import math
from datetime import datetime, timedelta

def hash_pass(password: str) -> str:

    salt = secrets.token_hex(16) 
    salted_password = password + salt
    hashed = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return f"{hashed}${salt}"  # store hash and salt together

def verify(plain_password: str, hash_password: str) -> bool:
    try:
        stored_hash, salt = hash_password.split('$')
        salted_password = plain_password + salt
        computed_hash = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False

def generate_otp():
    # 6 digit OTP generate hota hai
    return str(random.randint(100000, 999999))

def otp_expiry_time():
    # OTP 10 minutes ke liye valid
    return datetime.utcnow() + timedelta(minutes=10)
    
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def within_time_window(ride_time: datetime, target_time: datetime, margin_minutes: int = 20):
    lower = target_time - timedelta(minutes=margin_minutes)
    upper = target_time + timedelta(minutes=margin_minutes)
    return lower <= ride_time <= upper

    


