import os
import shutil
import json
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from database.connection import get_db
from models.user import User, Admin, OTPVerification
from schemas.auth import UserRegister, UserLogin, UserResponse, UserUpdate, AdminRegister, AdminLogin, AdminResponse, AdminUpdate
from services.auth_service import auth_service
from config import settings
from typing import List
from pydantic import BaseModel, EmailStr

router = APIRouter()

# --- CUSTOMER AUTH ---

# --- ASYNC BROADCAST HELPER ---
async def broadcast_admin_notification(message: dict):
    from routers.notifications import manager
    await manager.broadcast(message)

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == payload.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check OTP verification state
    otp_check = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.verified == True
    ).first()
    
    if not otp_check:
        raise HTTPException(
            status_code=400,
            detail="Email address not verified via OTP. Please verify your email first."
        )
    
    hashed_pwd = auth_service.get_password_hash(payload.password)
    name_val = payload.name or payload.full_name or ""
    user = User(
        email=payload.email,
        password=hashed_pwd,
        name=name_val,
        phone=payload.phone,
        gender=payload.gender,
        dob=payload.dob,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send welcome email asynchronously
    try:
        from services.email_service import send_welcome_email
        send_welcome_email(user.email, user.name)
    except Exception as email_err:
        print(f"Failed to send welcome email: {email_err}")

    # Broadcast to admins
    background_tasks.add_task(broadcast_admin_notification, {
        "title": "New Customer Registered",
        "message": f"{name_val} ({payload.email}) just created an account.",
        "type": "new_customer",
        "email": payload.email
    })
        
    return {
        "status": "success", 
        "message": "User registered successfully", 
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "full_name": user.name,
            "phone": user.phone or "",
            "gender": user.gender or "",
            "dob": user.dob or "",
            "address": user.address or "",
            "city": user.city or "",
            "state": user.state or "",
            "pincode": user.pincode or "",
            "district": user.district or "",
            "country": user.country or "",
            "profile_image": user.profile_image or ""
        }
    }

@router.post("/auth/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not auth_service.verify_password(payload.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    return {
        "status": "success",
        "message": "Login successful",
        "role": "customer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "full_name": user.name,
            "phone": user.phone or "",
            "gender": user.gender or "",
            "dob": user.dob or "",
            "address": user.address or "",
            "city": user.city or "",
            "state": user.state or "",
            "pincode": user.pincode or "",
            "district": user.district or "",
            "country": user.country or "",
            "profile_image": user.profile_image or ""
        }
    }

@router.get("/auth/profile/{email}")
def get_user_profile(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "status": "success", 
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "full_name": user.name,
            "phone": user.phone or "",
            "gender": user.gender or "",
            "dob": user.dob or "",
            "address": user.address or "",
            "city": user.city or "",
            "state": user.state or "",
            "pincode": user.pincode or "",
            "district": user.district or "",
            "country": user.country or "",
            "profile_image": user.profile_image or ""
        }
    }

@router.put("/auth/profile/{email}")
def update_user_profile(email: str, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = payload.dict(exclude_unset=True)
    if "full_name" in data and data["full_name"] is not None:
        user.name = data["full_name"]
    if "name" in data and data["name"] is not None:
        user.name = data["name"]
        
    for key, value in data.items():
        if key not in ["name", "full_name"] and value is not None:
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return {
        "status": "success", 
        "message": "Profile updated", 
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "full_name": user.name,
            "phone": user.phone or "",
            "gender": user.gender or "",
            "dob": user.dob or "",
            "address": user.address or "",
            "city": user.city or "",
            "state": user.state or "",
            "pincode": user.pincode or "",
            "district": user.district or "",
            "country": user.country or "",
            "profile_image": user.profile_image or ""
        }
    }

@router.post("/auth/profile/{email}/avatar")
def upload_user_avatar(email: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"avatar_{user.id}{file_ext}"
    filepath = os.path.join(settings.PROFILE_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url_path = f"{settings.SERVER_BASE_URL}/{settings.PROFILE_UPLOAD_DIR}/{filename}"
    user.profile_image = url_path
    db.commit()
    db.refresh(user)
    
    return {"status": "success", "profile_image": url_path}


# --- ADMIN AUTH ---

@router.post("/admin/register", status_code=status.HTTP_201_CREATED)
def register_admin(payload: AdminRegister, db: Session = Depends(get_db)):
    # Limit admin accounts to maximum 3
    admin_count = db.query(Admin).count()
    if admin_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum Admin Limit Reached"
        )

    db_admin = db.query(Admin).filter(Admin.email == payload.email).first()
    if db_admin:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Require OTP verification before creating admin account
    otp_check = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.verified == True
    ).first()

    if not otp_check:
        raise HTTPException(
            status_code=400,
            detail="Email address not verified via OTP. Please verify your email first."
        )

    hashed_pwd = auth_service.get_password_hash(payload.password)
    admin = Admin(
        email=payload.email,
        password=hashed_pwd,
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Send welcome email
    try:
        from services.email_service import send_welcome_email
        send_welcome_email(admin.email, admin.full_name)
    except Exception as email_err:
        print(f"Failed to send welcome email: {email_err}")

    return {
        "status": "success",
        "message": "Admin registered successfully",
        "admin": {
            "id": admin.id,
            "email": admin.email,
            "full_name": admin.full_name,
            "phone": admin.phone or "",
            "profile_image": admin.profile_image or "",
            "role": admin.role
        }
    }

@router.get("/admin/check-limit")
def check_admin_limit(db: Session = Depends(get_db)):
    """Returns whether the admin registration limit (3) has been reached."""
    count = db.query(Admin).count()
    limit_reached = count >= 3
    return {"count": count, "limit": 3, "limit_reached": limit_reached}

@router.post("/admin/login")
def login_admin(payload: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == payload.email).first()
    if not admin or not auth_service.verify_password(payload.password, admin.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    return {
        "status": "success",
        "message": "Login successful",
        "role": "admin",
        "admin": {
            "id": admin.id,
            "email": admin.email,
            "full_name": admin.full_name,
            "phone": admin.phone or "",
            "profile_image": admin.profile_image or "",
            "role": admin.role
        }
    }

@router.get("/admin/profile/{email}")
def get_admin_profile(email: str, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"status": "success", "admin": admin}

@router.put("/admin/profile/{email}")
def update_admin_profile(email: str, payload: AdminUpdate, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(admin, key, value)
    
    db.commit()
    db.refresh(admin)
    return {"status": "success", "message": "Admin profile updated", "admin": admin}

@router.post("/admin/profile/{email}/avatar")
def upload_admin_avatar(email: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"admin_avatar_{admin.id}{file_ext}"
    filepath = os.path.join(settings.PROFILE_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url_path = f"{settings.SERVER_BASE_URL}/{settings.PROFILE_UPLOAD_DIR}/{filename}"
    admin.profile_image = url_path
    db.commit()
    db.refresh(admin)
    
    return {"status": "success", "profile_image": url_path}


# ─────────────────────────────────────────────────────────────────
# PASSWORD RESET  (OTP-based — works for customers AND admins)
# ─────────────────────────────────────────────────────────────────

class SendResetOtpRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


@router.post("/auth/send-reset-otp")
def send_reset_otp(payload: SendResetOtpRequest, db: Session = Depends(get_db)):
    """
    Sends a 6-digit OTP to the entered email for password reset.
    Checks if the email exists in either customers or admins table.
    """
    email = payload.email
    print(f"\n[RESET-OTP] Request for: {email}")

    # Validate email registration state
    user_exists = db.query(User).filter(User.email == email).first()
    admin_exists = db.query(Admin).filter(Admin.email == email).first()

    if not user_exists and not admin_exists:
        print(f"[RESET-OTP] ❌ Email {email} not registered")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered. Please create an account first."
        )

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    print(f"[RESET-OTP] Generated OTP for {email}")

    # Send OTP via real Gmail SMTP first
    from services.email_service import send_otp_email
    result = send_otp_email(email, otp)

    if not result["success"]:
        print(f"[RESET-OTP] ❌ Email failed: {result['message']}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Failed to send OTP email"
            }
        )

    print(f"[RESET-OTP] ✅ OTP email sent to {email}")

    # Remove any existing OTPs for this email
    db.query(OTPVerification).filter(OTPVerification.email == email).delete()
    db.commit()

    # Save fresh OTP with 5-minute expiry
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db_otp = OTPVerification(
        email=email,
        otp=otp,
        expires_at=expires_at,
        verified=False
    )
    db.add(db_otp)
    db.commit()
    print(f"[RESET-OTP] Saved to DB, expires: {expires_at} UTC")

    return {
        "success": True,
        "message": "OTP sent to your email. Valid for 5 minutes."
    }



@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Verifies the OTP then updates the password in the database.
    Password is hashed using pbkdf2_sha256 before saving.
    """
    email        = payload.email
    otp          = payload.otp
    new_password = payload.new_password

    print(f"\n[RESET-PWD] Request for: {email}")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Validate OTP from database
    now = datetime.utcnow()
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == email,
        OTPVerification.otp   == otp,
        OTPVerification.expires_at >= now
    ).order_by(OTPVerification.id.desc()).first()

    if not db_otp:
        print(f"[RESET-PWD] ❌ Invalid/expired OTP for {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new one."
        )

    # Hash the new password
    hashed_pwd = auth_service.get_password_hash(new_password)
    print(f"[RESET-PWD] Hashed new password for {email}")

    # Update customer password
    updated = False
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.password = hashed_pwd
        updated = True
        print(f"[RESET-PWD] ✅ Customer password updated for {email}")

    # Update admin password (same email can be admin)
    admin = db.query(Admin).filter(Admin.email == email).first()
    if admin:
        admin.password = hashed_pwd
        updated = True
        print(f"[RESET-PWD] ✅ Admin password updated for {email}")

    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Delete the used OTP so it cannot be reused
    db.delete(db_otp)
    db.commit()
    print(f"[RESET-PWD] OTP deleted, reset complete for {email}")

    return {
        "success": True,
        "message": "Password reset successfully. You can now login with your new password."
    }
