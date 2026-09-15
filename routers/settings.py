import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.connection import get_db
from models.setting import PaymentSetting, QrCode, DeliverySetting, StoreSetting
from schemas.setting import PaymentSettingResponse, PaymentSettingUpdate, QrCodeResponse, DeliverySettingResponse, DeliverySettingUpdate, StoreSettingResponse, StoreSettingUpdate
from config import settings
from services.storage_service import storage_service
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
    deliv = db.query(DeliverySetting).filter(DeliverySetting.id == 1).first()
    if not deliv:
        deliv = DeliverySetting(id=1, standard_name="Standard Delivery", standard_days="3-5 days", standard_price=0, express_name="Express Delivery", express_days="1-2 days", express_price=79)
        db.add(deliv)
        db.commit()
        db.refresh(deliv)
    return {
        "standard_delivery_charge": deliv.standard_price,
        "express_delivery_charge": deliv.express_price,
        "standard_delivery_name": deliv.standard_name,
        "standard_delivery_days": deliv.standard_days,
        "express_delivery_name": deliv.express_name,
        "express_delivery_days": deliv.express_days
    }

@router.put("/settings/delivery-charge")
def update_delivery_charge(express_charge: int, db: Session = Depends(get_db)):
    deliv = db.query(DeliverySetting).filter(DeliverySetting.id == 1).first()
    if not deliv:
        deliv = DeliverySetting(id=1)
        db.add(deliv)
    deliv.express_price = express_charge
    setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
    if setup:
        setup.express_delivery_charge = express_charge
    db.commit()
    return {
        "status": "success",
        "standard_delivery_charge": deliv.standard_price,
        "express_delivery_charge": deliv.express_price,
        "standard_delivery_name": deliv.standard_name,
        "standard_delivery_days": deliv.standard_days,
        "express_delivery_name": deliv.express_name,
        "express_delivery_days": deliv.express_days
    }

@router.get("/settings/delivery", response_model=DeliverySettingResponse)
def get_delivery_settings_full(db: Session = Depends(get_db)):
    deliv = db.query(DeliverySetting).filter(DeliverySetting.id == 1).first()
    if not deliv:
        deliv = DeliverySetting(id=1, standard_name="Standard Delivery", standard_days="3-5 days", standard_price=0, express_name="Express Delivery", express_days="1-2 days", express_price=79)
        db.add(deliv)
        db.commit()
        db.refresh(deliv)
    return deliv

@router.put("/settings/delivery", response_model=DeliverySettingResponse)
def update_delivery_settings_full(payload: DeliverySettingUpdate, db: Session = Depends(get_db)):
    deliv = db.query(DeliverySetting).filter(DeliverySetting.id == 1).first()
    if not deliv:
        deliv = DeliverySetting(id=1)
        db.add(deliv)
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(deliv, key, value)
    if payload.express_price is not None:
        setup = db.query(PaymentSetting).filter(PaymentSetting.id == 1).first()
        if setup:
            setup.express_delivery_charge = payload.express_price
    db.commit()
    db.refresh(deliv)
    return deliv

@router.get("/settings/store", response_model=StoreSettingResponse)
def get_store_settings(db: Session = Depends(get_db)):
    store = db.query(StoreSetting).filter(StoreSetting.id == 1).first()
    if not store:
        store = StoreSetting(id=1, low_stock_threshold=5)
        db.add(store)
        db.commit()
        db.refresh(store)
    return store

@router.put("/settings/store", response_model=StoreSettingResponse)
def update_store_settings(payload: StoreSettingUpdate, db: Session = Depends(get_db)):
    store = db.query(StoreSetting).filter(StoreSetting.id == 1).first()
    if not store:
        store = StoreSetting(id=1)
        db.add(store)
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store



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
            if db_qr.image_path:
                storage_service.delete_image(db_qr.image_path)
            db_qr.image_path = ""
            db.commit()
        return {"status": "success", "message": f"QR code for {provider} deactivated"}
        
    # Standard save or update
    image_url = db_qr.image_path if db_qr else ""
    
    if qr_image:
        if db_qr and db_qr.image_path:
            storage_service.delete_image(db_qr.image_path)

        file_ext = os.path.splitext(qr_image.filename)[1]
        filename = f"qr_{provider.lower().replace(' ', '_')}_{int(time.time())}{file_ext}"
        image_url = storage_service.upload_image(qr_image.file, filename, folder="qr_codes")

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
