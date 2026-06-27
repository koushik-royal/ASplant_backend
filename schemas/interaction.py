from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from schemas.product import ProductResponse

class WishlistToggle(BaseModel):
    product_id: int

class WishlistResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    product: ProductResponse

    class Config:
        from_attributes = True

class CartCreate(BaseModel):
    product_id: int
    quantity: int

class CartUpdate(BaseModel):
    quantity: int

class CartResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    # Android reads the field as 'plant', so we alias it
    plant: Optional[ProductResponse] = Field(None, alias="product")

    model_config = {"from_attributes": True, "populate_by_name": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Allow both 'product' (SQLAlchemy) and 'plant' (direct) as the source
        return super().model_validate(obj, *args, **kwargs)

class RatingCreate(BaseModel):
    order_id: str
    rating: float
    review: Optional[str] = ""

class RatingResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    order_id: str
    rating: float
    review: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
