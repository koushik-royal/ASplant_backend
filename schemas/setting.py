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

class DeliverySettingUpdate(BaseModel):
    standard_name: Optional[str] = None
    standard_days: Optional[str] = None
    standard_price: Optional[int] = None
    express_name: Optional[str] = None
    express_days: Optional[str] = None
    express_price: Optional[int] = None

class DeliverySettingResponse(BaseModel):
    id: int
    standard_name: str
    standard_days: str
    standard_price: int
    express_name: str
    express_days: str
    express_price: int

    class Config:
        from_attributes = True

class StoreSettingUpdate(BaseModel):
    low_stock_threshold: Optional[int] = None

class StoreSettingResponse(BaseModel):
    id: int
    low_stock_threshold: int

    class Config:
        from_attributes = True

