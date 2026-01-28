from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Float, text, ForeignKey, DateTime, Boolean
from .database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

class DSUStudent(Base):
    __tablename__ = "dsu_students"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    dsu_reg_id = Column(String(20), nullable=False, unique=True, index=True)
    department = Column(String(50), nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    dsu_reg_id = Column(String(20), nullable=False, unique=True)
    phone_number = Column(String(15), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    gender = Column(String(50), nullable=False)
    role = Column(String(10), nullable=False)  # passenger / driver
    nic_image_url = Column(Text, nullable=True) #for driver only
    live_image_url = Column(Text, nullable=True) #for driver only - face verification
    license_image_url = Column(Text, nullable=True) # for driver only

        # 🔐 SIGNUP VERIFICATION (OTP)
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String(6), nullable=True)     #preety change
    otp_expiry = Column(DateTime, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True),nullable=False,server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))

    vehicles = relationship("Vehicle", back_populates="user", cascade="all, delete")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),nullable=False)
    mode_of_transport = Column(String(10), nullable=False)  # car / bike
    vehicle_number = Column(String(20), nullable=False)
   # license_image_url = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    user = relationship("User", back_populates="vehicles")


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False) 

    from_address = Column(String, nullable=False)
    from_lat = Column(Float, nullable=False)
    from_lng = Column(Float, nullable=False)

    to_address = Column(String, nullable=False)
    to_lat = Column(Float, nullable=False)
    to_lng = Column(Float, nullable=False)

    departure_time = Column(DateTime, nullable=False)
    seats_available = Column(Integer, nullable=False)
    ac = Column(Boolean)
    gender_filter = Column(String, default="any")
    fare_per_seat = Column(Float)

    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    driver = relationship("User")
    vehicle = relationship("Vehicle") 
    
    @property
    def mode_of_transport(self):
        return self.vehicle.mode_of_transport if self.vehicle else "unknown"


class RideRequest(Base):
    __tablename__ = "ride_requests"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id"))
    passenger_id = Column(Integer, ForeignKey("users.id"))

    status = Column(String, default="pending")  # pending / accepted / rejected
    distance_from_route = Column(Float)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

    ride = relationship("Ride")
    passenger = relationship("User")



