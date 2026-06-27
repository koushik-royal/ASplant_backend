import os
import shutil
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.connection import get_db
from models.user import User, OTPVerification
from services.email_service import send_otp_email
from config import settings
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()

# --- PYDANTIC SCHEMAS ---

class SendOtpRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ProfileUpdatePayload(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    district: Optional[str] = None
    country: Optional[str] = None

# --- OTP LOGIC ---

@router.post("/customer/send-otp")
def send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    email = payload.email

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"

    print(f"\n[OTP] Sending OTP to: {email}")

    # --- Send email FIRST; only save to DB if delivery succeeds ---
    result = send_otp_email(email, otp)

    if not result["success"]:
        print(f"[OTP] ❌ Email delivery FAILED for {email}")
        print(f"[OTP] Error: {result['message']}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Failed to send OTP email"
            }
        )

    print(f"[OTP] ✅ OTP email delivered to {email}")

    # Email delivered — clean up old OTPs for this email (supports Resend)
    db.query(OTPVerification).filter(OTPVerification.email == email).delete()
    db.commit()

    # Save new OTP with 5-minute expiry
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db_otp = OTPVerification(
        email=email,
        otp=otp,
        expires_at=expires_at,
        verified=False
    )
    db.add(db_otp)
    db.commit()

    print(f"[OTP] Saved to DB with expiry: {expires_at} UTC")

    return {
        "success": True,
        "message": "OTP sent successfully to email"
    }


@router.post("/customer/verify-otp")
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    email = payload.email
    otp = payload.otp
    
    print(f"\n[VERIFY-OTP] Request for: {email}")

    # Query database for the latest non-expired matching OTP
    now = datetime.utcnow()
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == email,
        OTPVerification.otp == otp,
        OTPVerification.expires_at >= now
    ).order_by(OTPVerification.id.desc()).first()
    
    if not db_otp:
        print(f"[VERIFY-OTP] ❌ Invalid or expired OTP for {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    db_otp.verified = True
    db.commit()
    
    print(f"[VERIFY-OTP] ✅ OTP verified successfully for {email}")
        
    return {
        "success": True,
        "message": "OTP verified successfully"
    }

# --- CUSTOMER PROFILE ---

@router.get("/customer/profile")
def get_customer_profile(email: str, db: Session = Depends(get_db)):
    customer = db.query(User).filter(User.email == email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
        
    created_str = customer.created_at.strftime("%d %b %Y") if customer.created_at else ""
        
    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone or "",
            "profile_image": customer.profile_image or "",
            "created_at": created_str,
            "gender": customer.gender or "",
            "dob": customer.dob or "",
            "address": customer.address or "",
            "city": customer.city or "",
            "state": customer.state or "",
            "pincode": customer.pincode or "",
            "district": customer.district or "",
            "country": customer.country or ""
        }
    }

@router.put("/customer/update-profile")
def update_customer_profile(email: str, payload: ProfileUpdatePayload, db: Session = Depends(get_db)):
    customer = db.query(User).filter(User.email == email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
        
    # Exclude unset fields
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            if field == "full_name":
                customer.name = value
            elif field == "name":
                customer.name = value
            else:
                setattr(customer, field, value)
            
    db.commit()
    db.refresh(customer)
    
    created_str = customer.created_at.strftime("%d %b %Y") if customer.created_at else ""
    
    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone or "",
            "profile_image": customer.profile_image or "",
            "created_at": created_str,
            "gender": customer.gender or "",
            "dob": customer.dob or "",
            "address": customer.address or "",
            "city": customer.city or "",
            "state": customer.state or "",
            "pincode": customer.pincode or "",
            "district": customer.district or "",
            "country": customer.country or ""
        }
    }

@router.post("/customer/upload-profile-image")
def upload_customer_profile_image(email: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    customer = db.query(User).filter(User.email == email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
        
    # Create file name based on customer ID
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"profile_{customer.id}{file_ext}"
    filepath = os.path.join(settings.PROFILE_IMAGES_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url_path = f"{settings.SERVER_BASE_URL}/{settings.PROFILE_IMAGES_DIR}/{filename}"
    customer.profile_image = url_path
    db.commit()
    db.refresh(customer)
    
    created_str = customer.created_at.strftime("%d %b %Y") if customer.created_at else ""
    
    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone or "",
            "profile_image": url_path,
            "created_at": created_str,
            "gender": customer.gender or "",
            "dob": customer.dob or "",
            "address": customer.address or "",
            "city": customer.city or "",
            "state": customer.state or "",
            "pincode": customer.pincode or "",
            "district": customer.district or "",
            "country": customer.country or ""
        }
    }
