# pyrefly: ignore [missing-import]
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
    temperature: Optional[str] = None
    humidity: Optional[str] = None
    pot_size: Optional[str] = None
    stock: Optional[int] = None
    images: Optional[List[str]] = []
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

def to_full_url(path: Optional[str]) -> str:
    if not path:
        return ""
    p = path.strip()
    if not p or p.startswith("res:"):
        return p
    from config import settings
    base = (settings.SERVER_BASE_URL or "https://asplant-backend-1.onrender.com").rstrip("/")
    if ":8000" in p:
        sub = p.split(":8000", 1)[1]
        return f"{base}{sub}"
    if "asplant-backend.onrender.com" in p and "asplant-backend-1.onrender.com" not in p:
        p = p.replace("https://asplant-backend.onrender.com", base).replace("http://asplant-backend.onrender.com", base)
    if p.startswith("http://") or p.startswith("https://"):
        return p
    if p.startswith("/"):
        return f"{base}{p}"
    return f"{base}/{p}"

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    benefits: Optional[str] = None
    watering: Optional[str] = None
    sunlight: Optional[str] = None
    temperature: Optional[str] = None
    humidity: Optional[str] = None
    pot_size: Optional[str] = None
    id: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    stock_quantity: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    is_featured: Optional[bool] = None
    detailed_description: Optional[str] = None
    image_url: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    category_id: int
    category: str = "" # Category string name like 'Succulents' for Java Plant compatibility
    rating: float
    reviews_count: int
    image_url: Optional[str] = ""
    imagePaths: List[str] = [] # Flat list of image URLs for Java Plant compatibility
    stock: int = 25
    images: List[str] = []

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def resolve_java_compat_fields(cls, data):
        if not isinstance(data, dict):
            # SQLAlchemy model conversion to dictionary for custom fields
            image_url_val = to_full_url(getattr(data, 'image_url', ''))
            images_list = []
            seen = set()
            if hasattr(data, 'images') and data.images:
                sorted_images = sorted(data.images, key=lambda x: getattr(x, 'display_order', 0) if getattr(x, 'display_order', 0) is not None else 0)
                for img in sorted_images:
                    full_p = to_full_url(img.image_path)
                    if full_p and full_p not in seen:
                        seen.add(full_p)
                        images_list.append(full_p)
            if not images_list and image_url_val:
                images_list = [image_url_val]
            elif images_list and not image_url_val:
                image_url_val = images_list[0]
            
            cat_val = getattr(data, 'category_name', '')
            if not cat_val and hasattr(data, 'category') and data.category:
                cat_val = getattr(data.category, 'name', '') or ""

            prod_dict = {
                "id": data.id,
                "name": data.name,
                "price": data.price,
                "description": data.description,
                "benefits": data.benefits,
                "watering": data.watering,
                "sunlight": data.sunlight,
                "temperature": data.temperature,
                "humidity": data.humidity,
                "pot_size": data.pot_size,
                "is_active": data.is_active,
                "status": getattr(data, 'status', 'active'),
                "stock_quantity": data.stock_quantity,
                "stock": getattr(data, 'stock_quantity', 25),
                "height": data.height,
                "weight": data.weight,
                "is_featured": data.is_featured,
                "detailed_description": data.detailed_description,
                "category_id": data.category_id,
                "category": cat_val,
                "rating": data.rating,
                "reviews_count": data.reviews_count,
                "image_url": image_url_val,
                "imagePaths": images_list,
                "images": images_list
            }
            return prod_dict
        else:
            if "image_url" in data:
                data["image_url"] = to_full_url(data["image_url"])
            if not data.get("imagePaths") and data.get("image_url"):
                data["imagePaths"] = [data["image_url"]]
            if data.get("imagePaths"):
                data["imagePaths"] = list(dict.fromkeys([to_full_url(p) for p in data["imagePaths"] if p]))
            
            data["images"] = data.get("imagePaths", [])
            if not data.get("image_url") and data.get("images"):
                data["image_url"] = data["images"][0]
            if "stock_quantity" in data and "stock" not in data:
                data["stock"] = data["stock_quantity"]
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
