from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
from typing import Optional, List, Literal
from datetime import datetime

TransportMode = Literal["car", "bike"]

class RideStatus(str, Enum):
    active = "active"
    full = "full"
    cancelled = "cancelled"
    completed = "completed"

class RideRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled_by_passenger = "cancelled_by_passenger"
    cancelled_by_driver = "cancelled_by_driver"

class UserBase(BaseModel):
    first_name: str
    last_name: str
    dsu_reg_id: str
    phone_number: str
    email: EmailStr
    gender: str

class VehicleCreate(BaseModel):
    vehicle_number: str
    mode_of_transport: TransportMode
    vehicle_model: str
    vehicle_colour: str

class DriverCreate(UserBase):
    password: str
    license_image_url: str
    cnic_image_url: str
    live_image_url: str
    vehicles: List[VehicleCreate]


class PassengerCreate(UserBase):
    password: str

class DriverEnable(BaseModel):
    dsu_reg_id: str
    license_image_url: str
    cnic_image_url: str
    live_image_url: str
    vehicles: List[VehicleCreate]

# what frontend needs to show correct screen
class MeOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    dsu_reg_id: str
    phone_number: str
    email: EmailStr
    gender: str
    is_passenger: bool
    is_driver: bool
    active_mode: str
    driver_profile_complete: bool

class SwitchMode(BaseModel):
    mode: Literal["passenger", "driver"]


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    dsu_reg_id: str
    phone_number: str
    role: str
    is_passenger: bool
    is_driver: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int


class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str


class ResendOTP(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class RideCreate(BaseModel):
    vehicle_id: int
    from_address: str
    from_lat: float
    from_lng: float
    to_address: str
    to_lat: float
    to_lng: float
    departure_time: datetime
    seats_available: Optional[int] = None     #frontend can omit for bike
    ac: Optional[bool] = None  #required for car, not allowed for bike
    gender_filter: str = "any"
    fare_per_seat: float = 0.0

    @field_validator("fare_per_seat")
    def validate_fare(cls, v):
        if v < 0:
            raise ValueError("fare_per_seat cannot be negative")
        return v

class RideOut(BaseModel):
    id: int
    driver_id: int
    vehicle_id: int
    from_address: str
    to_address: str
    departure_time: datetime
    seats_available: int
    ac: Optional[bool] = None
    gender_filter: Optional[str] = None
    fare_per_seat: float
    mode_of_transport: Optional[str] = None
    status: Optional[str] = None  # or RideStatus

    class Config:
        from_attributes = True

class RideRequestCreate(BaseModel):
    ride_id: int
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None

class RideRequestOut(BaseModel):
    id: int
    ride_id: int
    status: RideRequestStatus
    distance_from_route: float

    class Config:
        from_attributes = True


class TokenRequest(BaseModel):   #notification system
    user_id: int
    token: str

class LocationUpdate(BaseModel):
    ride_id: int
    latitude: float
    longitude: float
    driver_id: int

class LocationResponse(BaseModel):
    ride_id: int
    driver_id: int
    latitude: float
    longitude: float
    eta_seconds: Optional[int] = None
    eta_minutes: Optional[int] = None

    class Config:
        from_attributes = True