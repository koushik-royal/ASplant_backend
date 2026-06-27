from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.product import ProductResponse

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: int

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: int
    plant: Optional[ProductResponse] = None
    is_rated: Optional[bool] = False

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    subtotal: int
    delivery_charge: int
    total_amount: int
    full_name: str
    phone_number: str
    pincode: str
    address_line: str
    landmark: Optional[str] = ""
    city: str
    state: str
    district: Optional[str] = ""
    country: Optional[str] = ""
    address_type: Optional[str] = "HOME"
    delivery_option: Optional[str] = "Standard Delivery"
    payment_method: str

    transaction_id: Optional[str] = None
    items: List[OrderItemCreate]

class OrderUpdateStatus(BaseModel):
    status: str

class DeliveryTrackingResponse(BaseModel):
    id: int
    order_id: str
    status: str
    timestamp: datetime
    remarks: Optional[str]

    class Config:
        from_attributes = True

class DeliveryProofResponse(BaseModel):
    id: int
    order_id: str
    image_path: str
    signature_path: str
    verified_at: datetime

    class Config:
        from_attributes = True

class PaymentResponse(BaseModel):
    id: int
    order_id: str
    user_id: int
    payment_method: str
    amount: int
    transaction_id: str
    status: str
    screenshot_path: str
    verified_at: Optional[datetime]
    verified_by: Optional[int]

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    order_id: str
    user_id: int
    date: str
    status: str
    subtotal: int
    delivery_charge: int
    total_amount: int
    full_name: str
    phone_number: str
    pincode: str
    address_line: str
    landmark: Optional[str]
    city: str
    state: str
    district: Optional[str] = ""
    country: Optional[str] = ""
    address_type: str
    delivery_option: str
    payment_method: str
    payment_status: Optional[str] = "UNPAID"

    screenshot_path: Optional[str] = ""
    transaction_id: Optional[str] = ""
    delivery_proof_path: str
    customer_signature_path: str
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
