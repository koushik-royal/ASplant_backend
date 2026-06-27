import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.connection import get_db
from models.setting import PaymentSetting, QrCode
from schemas.setting import PaymentSettingResponse, PaymentSettingUpdate, QrCodeResponse
from config import settings
from typing import List, Optional

router = APIRouter()

# --- PAYMENT SETTINGS ---

@router.get("/settings/payment", response_model=PaymentSettingResponse)
def get_payment_settings(db: Session = Depends(get_db)):
    setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
    if not setup:
        # Create default
        setup = PaymentSetting(id=1, cod_enabled=True, bank_name="State Bank of India", account_number="123456789012", ifsc_code="SBIN0001234", account_holder="AS Plants Admin", express_delivery_charge=79)
        db.add(setup)
        db.commit()
        db.refresh(setup)
    return setup

@router.put("/settings/payment", response_model=PaymentSettingResponse)
def update_payment_settings(payload: PaymentSettingUpdate, db: Session = Depends(get_db)):
    setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
    if not setup:
        setup = PaymentSetting(id=1)
        db.add(setup)
        
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(setup, key, value)
        
    db.commit()
    db.refresh(setup)
    return setup

@router.get("/settings/delivery-charge")
def get_delivery_charge(db: Session = Depends(get_db)):
    setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
    charge = setup.express_delivery_charge if setup else 79
    return {"standard_delivery_charge": 0, "express_delivery_charge": charge}

@router.put("/settings/delivery-charge")
def update_delivery_charge(express_charge: int, db: Session = Depends(get_db)):
    setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
    if not setup:
        setup = PaymentSetting(id=1)
        db.add(setup)
    setup.express_delivery_charge = express_charge
    db.commit()
    return {"status": "success", "standard_delivery_charge": 0, "express_delivery_charge": express_charge}


# --- UPI QR CODES ---

@router.get("/settings/qr-codes", response_model=List[QrCodeResponse])
def get_qr_codes(db: Session = Depends(get_db)):
    return db.query(QrCode).filter(QrCode.is_active == True).all()


# Compatibility endpoint for Android uploadQr() in HttpHelper.java
@router.post("/upload_qr.php")
def compatibility_upload_qr(
    provider: str = Form(...),
    upi_id: Optional[str] = Form(None),
    account_holder: Optional[str] = Form(None),
    delete: Optional[str] = Form(None),
    qr_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    import time
    # Check if delete operation requested
    is_delete = delete == "true"
    
    # Query active QR code for provider
    db_qr = db.query(QrCode).filter(QrCode.provider == provider).first()
    
    if is_delete:
        if db_qr:
            db_qr.is_active = False
            # Clean up old file
            if db_qr.image_path:
                try:
                    old_filename = os.path.basename(db_qr.image_path)
                    old_filepath = os.path.join(settings.QR_UPLOAD_DIR, old_filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                except Exception as e:
                    print("Error deleting old QR file:", e)
            db_qr.image_path = ""
            db.commit()
        return {"status": "success", "message": f"QR code for {provider} deactivated"}
        
    # Standard save or update
    image_url = db_qr.image_path if db_qr else ""
    
    if qr_image:
        # Delete old QR file if replacing
        if db_qr and db_qr.image_path:
            try:
                old_filename = os.path.basename(db_qr.image_path)
                old_filepath = os.path.join(settings.QR_UPLOAD_DIR, old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            except Exception as e:
                print("Error deleting old QR file:", e)

        file_ext = os.path.splitext(qr_image.filename)[1]
        filename = f"qr_{provider.lower().replace(' ', '_')}_{int(time.time())}{file_ext}"
        filepath = os.path.join(settings.QR_UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(qr_image.file, buffer)
            
        image_url = f"{settings.SERVER_BASE_URL}/{settings.QR_UPLOAD_DIR}/{filename}"

    if db_qr:
        db_qr.upi_id = upi_id or db_qr.upi_id
        if account_holder:
            db_qr.account_holder = account_holder
        if qr_image:
            db_qr.image_path = image_url
        db_qr.is_active = True
    else:
        db_qr = QrCode(
            provider=provider,
            upi_id=upi_id or "",
            account_holder=account_holder or "AS Plants Admin",
            image_path=image_url,
            is_active=True
        )
        db.add(db_qr)
        
    db.commit()
    return {"status": "success", "message": f"QR code for {provider} uploaded/updated successfully", "image_path": image_url}
