from sqlalchemy import Column, Integer, String, DateTime, text, Boolean
from database.connection import Base

class User(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column("password_hash", String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    gender = Column(String(20))
    dob = Column(String(20))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(20))
    district = Column(String(100))
    country = Column(String(100))
    profile_image = Column(String(255), default="")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column("password_hash", String(255), nullable=False)
    full_name = Column("name", String(100), nullable=False)
    phone = Column(String(20))
    profile_image = Column(String(255), default="")
    role = Column(String(50), default="Admin")
    fcm_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    otp = Column(String(6), nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    expires_at = Column(DateTime, nullable=True)
