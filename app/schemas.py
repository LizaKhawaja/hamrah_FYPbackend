from pydantic import BaseModel, EmailStr, field_validator 
from enum import Enum 
from typing import Optional, List 
from datetime import datetime

class TransportMode(str, Enum):
    car = "car"
    bike = "bike"

class UserBase(BaseModel):
    first_name: str
    last_name: str
    dsu_reg_id: str
    phone_number: str
    email: EmailStr
    gender: str

class PassengerCreate(UserBase):
    password: str

# class VehicleCreate(BaseModel):
#     mode_of_transport: TransportMode
#     vehicle_number: str

# class DriverCreate(UserBase):
#     license_image_url: str # Store Firebase URL
#     vehicles: List[VehicleCreate] #can add more then 2 vehicles

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    dsu_reg_id: str
    phone_number: str
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: int  # User ID
    role: Optional[str] = None  # Optional role info

class OTPVerify(BaseModel): #Postman se hum email + otp bhejenge.
    email: EmailStr
    otp_code: str    

class ResendOTP(BaseModel):
    email: EmailStr

class RideCreate(BaseModel):
    vehicle_id: int                     # Vehicle chosen by driver
    from_address: str
    from_lat: float
    from_lng: float
    to_address: str
    to_lat: float
    to_lng: float
    departure_time: datetime
    seats_available: int = 1            # Set by driver; backend adjusts for bike
    ac: Optional[bool] = None           # Only car relevant; backend sets None for bike
    gender_filter: str = "any"
    fare_per_seat: float = 0.0          # Both bike & car; driver decides

    # Seats validation: at least 1
    @field_validator("seats_available")
    def check_seats(cls, v):
        if v < 1:
            raise ValueError("seats_available must be at least 1")
        return v

    # Fare validation
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
    gender_filter: str = None
    fare_per_seat: float
    mode_of_transport: str

    class Config:
        from_attributes = True  


class RideRequestCreate(BaseModel):
    ride_id: int


class RideRequestOut(BaseModel):
    id: int
    ride_id: int
    status: str
    distance_from_route: float

    class Config:
        from_attributes = True


