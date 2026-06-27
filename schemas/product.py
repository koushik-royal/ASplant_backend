from pydantic import BaseModel, model_validator
from typing import List, Optional

class ProductImageResponse(BaseModel):
    id: int
    product_id: int
    image_path: str

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    price: int
    description: Optional[str] = None
    benefits: Optional[str] = None
    watering: Optional[str] = None
    sunlight: Optional[str] = None
    pot_size: Optional[str] = None
    is_active: Optional[bool] = True
    status: Optional[str] = "active"
    stock_quantity: Optional[int] = 25
    height: Optional[str] = "30cm"
    weight: Optional[str] = "1.2kg"
    is_featured: Optional[bool] = False
    detailed_description: Optional[str] = ""

class ProductCreate(ProductBase):
    category_id: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = ""
    image_paths: Optional[List[str]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    benefits: Optional[str] = None
    watering: Optional[str] = None
    sunlight: Optional[str] = None
    pot_size: Optional[str] = None
    id: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    stock_quantity: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    is_featured: Optional[bool] = None
    detailed_description: Optional[str] = None
    image_url: Optional[str] = ""

class ProductResponse(ProductBase):
    id: int
    category_id: int
    category: str = "" # Category string name like 'Succulents' for Java Plant compatibility
    rating: float
    reviews_count: int
    image_url: Optional[str] = ""
    imagePaths: List[str] = [] # Flat list of image URLs for Java Plant compatibility

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def resolve_java_compat_fields(cls, data):
        if not isinstance(data, dict):
            # SQLAlchemy model conversion to dictionary for custom fields
            image_url_val = getattr(data, 'image_url', '')
            images_list = []
            seen = set()
            if hasattr(data, 'images') and data.images:
                sorted_images = sorted(data.images, key=lambda x: getattr(x, 'display_order', 0) if getattr(x, 'display_order', 0) is not None else 0)
                for img in sorted_images:
                    if img.image_path and img.image_path not in seen:
                        seen.add(img.image_path)
                        images_list.append(img.image_path)
            if not images_list and image_url_val:
                images_list = [image_url_val]
            
            prod_dict = {
                "id": data.id,
                "name": data.name,
                "price": data.price,
                "description": data.description,
                "benefits": data.benefits,
                "watering": data.watering,
                "sunlight": data.sunlight,
                "pot_size": data.pot_size,
                "is_active": data.is_active,
                "status": getattr(data, 'status', 'active'),
                "stock_quantity": data.stock_quantity,
                "height": data.height,
                "weight": data.weight,
                "is_featured": data.is_featured,
                "detailed_description": data.detailed_description,
                "category_id": data.category_id,
                "category": data.category.name if (hasattr(data, 'category') and data.category) else "",
                "rating": data.rating,
                "reviews_count": data.reviews_count,
                "image_url": image_url_val,
                "imagePaths": images_list
            }
            return prod_dict
        else:
            if not data.get("imagePaths") and data.get("image_url"):
                data["imagePaths"] = [data["image_url"]]
            if data.get("imagePaths"):
                data["imagePaths"] = list(dict.fromkeys([p for p in data["imagePaths"] if p]))
        return data

class CategoryCreate(BaseModel):
    name: str
    image_url: Optional[str] = ""

class CategoryResponse(BaseModel):
    id: int
    name: str
    image_url: str

    class Config:
        from_attributes = True
