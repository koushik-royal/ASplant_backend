from pydantic import BaseModel
from typing import Optional

class PaymentSettingUpdate(BaseModel):
    cod_enabled: Optional[bool] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder: Optional[str] = None
    express_delivery_charge: Optional[int] = None

class PaymentSettingResponse(BaseModel):
    id: int
    cod_enabled: bool
    bank_name: Optional[str]
    account_number: Optional[str]
    ifsc_code: Optional[str]
    account_holder: Optional[str]
    express_delivery_charge: int

    class Config:
        from_attributes = True

class QrCodeCreate(BaseModel):
    provider: str
    upi_id: str
    account_holder: Optional[str] = "AS Plants Admin"
    image_path: Optional[str] = ""
    is_active: Optional[bool] = True

class QrCodeResponse(BaseModel):
    id: int
    provider: str
    upi_id: str
    account_holder: str
    image_path: str
    is_active: bool

    class Config:
        from_attributes = True
