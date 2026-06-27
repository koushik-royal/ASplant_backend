import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from database.connection import get_db
from models.product import Product, Category, ProductImage
from models.order import Order, OrderItem
from models.user import User
from models.interaction import Cart, Wishlist
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from config import settings
from typing import List, Optional, Union

router = APIRouter()

# --- CATEGORIES ---

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/categories", response_model=CategoryResponse)
def create_category(
    name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    db_cat = db.query(Category).filter(Category.name == name).first()
    if db_cat:
        raise HTTPException(status_code=400, detail="Category already exists")
        
    image_url = ""
    if file:
        os.makedirs(settings.PRODUCT_UPLOAD_DIR, exist_ok=True)
        filename = f"cat_{name.lower().replace(' ', '_')}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(settings.PRODUCT_UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_url = f"{settings.SERVER_BASE_URL}/{settings.PRODUCT_UPLOAD_DIR}/{filename}"

    category = Category(name=name, image_url=image_url)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

# --- PRODUCTS ---

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    include_inactive: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    query = db.query(Product).options(joinedload(Product.images))
    if category and category != "All Plants":
        # Resolve category ID
        db_cat = db.query(Category).filter(Category.name == category).first()
        if db_cat:
            query = query.filter(Product.category_id == db_cat.id)
        else:
            return []
            
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
        
    if not include_inactive:
        query = query.filter(Product.status == "active")
    else:
        query = query.filter(Product.status != "deleted")
        
    return query.all()

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, email: Optional[str] = None, db: Session = Depends(get_db)):
    product = db.query(Product).options(joinedload(Product.images)).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # If product is soft-deleted, only return it to a customer who previously purchased it
    if product.status == "deleted":
        if not email:
            raise HTTPException(status_code=404, detail="Product not found")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Product not found")
        purchased = (
            db.query(OrderItem)
            .join(Order, Order.order_id == OrderItem.order_id)
            .filter(Order.user_id == user.id, OrderItem.product_id == product_id)
            .first()
        )
        if not purchased:
            raise HTTPException(status_code=404, detail="Product not found")

    return product

@router.post("/products", response_model=ProductResponse)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db)
):
    category_id = payload.category_id
    if not category_id and payload.category:
        db_cat = db.query(Category).filter(Category.name.ilike(payload.category)).first()
        if db_cat:
            category_id = db_cat.id
        else:
            category_id = 1
    elif not category_id:
        category_id = 1

    product = Product(
        name=payload.name,
        category_id=category_id,
        category_name=payload.category,
        price=payload.price,
        description=payload.description,
        benefits=payload.benefits,
        watering=payload.watering,
        sunlight=payload.sunlight,
        pot_size=payload.pot_size,
        is_active=payload.is_active,
        status="active" if payload.is_active else "inactive",
        stock_quantity=payload.stock_quantity,
        height=payload.height,
        weight=payload.weight,
        is_featured=payload.is_featured,
        image_url=payload.image_url or ""
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Process imagePaths if available
    if payload.image_paths:
        for idx, path in enumerate(payload.image_paths):
            if path and path.strip():
                prod_image = ProductImage(product_id=product.id, image_path=path.strip(), display_order=idx)
                db.add(prod_image)
        db.commit()
        db.refresh(product)
        # Set primary image_url if not set
        if not product.image_url and product.images:
            product.image_url = product.images[0].image_path
            db.commit()
            db.refresh(product)
            
    return product

@router.post("/products/images/upload-temp")
def upload_images_temp(
    files: List[UploadFile] = File(...)
):
    import time
    uploaded_urls = []
    os.makedirs(settings.PRODUCT_UPLOAD_DIR, exist_ok=True)
    
    for index, file in enumerate(files):
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"tmp_{int(time.time())}_{index}{file_ext}"
        filepath = os.path.join(settings.PRODUCT_UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        url_path = f"{settings.SERVER_BASE_URL}/{settings.PRODUCT_UPLOAD_DIR}/{filename}"
        uploaded_urls.append(url_path)
        
    return {"status": "success", "urls": uploaded_urls}

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    update_data = payload.dict(exclude_unset=True)
    if "category" in update_data:
        cat_name = update_data.pop("category")
        product.category_name = cat_name
        if cat_name:
            db_cat = db.query(Category).filter(Category.name.ilike(cat_name)).first()
            if db_cat:
                update_data["category_id"] = db_cat.id
            else:
                update_data["category_id"] = 1
                
    for key, value in update_data.items():
        setattr(product, key, value)
        
    if "status" in update_data:
        status_val = update_data["status"]
        if status_val == "active":
            product.is_active = True
        elif status_val == "inactive":
            product.is_active = False
    elif "is_active" in update_data:
        is_act_val = update_data["is_active"]
        product.status = "active" if is_act_val else "inactive"

    db.commit()
    db.refresh(product)
    return product

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).options(joinedload(Product.images)).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Soft-delete: mark product as deleted without removing it from the database.
    # This preserves the product reference in existing order items so that order
    # history, invoices, and the rating flow continue to work for past purchasers.
    product.status = "deleted"
    product.is_active = False

    # Remove deleted product from all active carts and wishlists so customers
    # cannot accidentally buy it through a stale session.
    db.query(Cart).filter(Cart.product_id == product_id).delete(synchronize_session=False)
    db.query(Wishlist).filter(Wishlist.product_id == product_id).delete(synchronize_session=False)

    db.commit()
    return {"status": "success", "message": "Product soft-deleted successfully"}

@router.post("/products/{product_id}/images")
def upload_product_images(
    product_id: int,
    kept_images: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    print(f"DEBUG: upload_product_images product_id={product_id}, files={files}")
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Parse kept_images safely
    kept_list = []
    if kept_images:
        if kept_images.startswith("["):
            import json
            try:
                kept_list = json.loads(kept_images)
            except Exception:
                kept_list = [img.strip() for img in kept_images.split(",") if img.strip()]
        else:
            kept_list = [img.strip() for img in kept_images.split(",") if img.strip()]
            
    # Normalize files to a list
    file_list = []
    if files:
        if isinstance(files, list):
            file_list = files
        else:
            file_list = [files]

    # Delete product images that are NOT in the kept list
    if kept_list:
        to_delete = db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ~ProductImage.image_path.in_(kept_list)
        ).all()
        for img in to_delete:
            if "uploads/products/" in img.image_path:
                filename = img.image_path.split("uploads/products/")[-1]
                local_file_path = os.path.join(settings.PRODUCT_UPLOAD_DIR, filename)
                if os.path.exists(local_file_path):
                    try:
                        os.remove(local_file_path)
                    except Exception as e:
                        print(f"Error removing physical image file during update: {e}")
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ~ProductImage.image_path.in_(kept_list)
        ).delete(synchronize_session=False)
    else:
        # If files are uploaded and no kept images are specified, delete all old images
        if file_list:
            to_delete = db.query(ProductImage).filter(ProductImage.product_id == product_id).all()
            for img in to_delete:
                if "uploads/products/" in img.image_path:
                    filename = img.image_path.split("uploads/products/")[-1]
                    local_file_path = os.path.join(settings.PRODUCT_UPLOAD_DIR, filename)
                    if os.path.exists(local_file_path):
                        try:
                            os.remove(local_file_path)
                        except Exception as e:
                            print(f"Error removing physical image file during complete clear: {e}")
            db.query(ProductImage).filter(ProductImage.product_id == product_id).delete()
        
    uploaded_images = list(kept_list)
    
    # Process newly uploaded files
    if file_list:
        for index, file in enumerate(file_list):
            file_ext = os.path.splitext(file.filename)[1]
            import time
            filename = f"prod_{product_id}_{int(time.time())}_{index}{file_ext}"
            filepath = os.path.join(settings.PRODUCT_UPLOAD_DIR, filename)
            
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            url_path = f"{settings.SERVER_BASE_URL}/{settings.PRODUCT_UPLOAD_DIR}/{filename}"
            
            prod_image = ProductImage(product_id=product_id, image_path=url_path)
            db.add(prod_image)
            uploaded_images.append(url_path)
            
    db.flush()
    # Fetch all current images for the product
    all_images = db.query(ProductImage).filter(ProductImage.product_id == product_id).all()
    all_paths = [img.image_path for img in all_images]
    
    if all_paths:
        product.image_url = all_paths[0]
    else:
        product.image_url = ""
        
    db.commit()
    return {"status": "success", "images": all_paths}

# --- COMPATIBILITY ALIASES ---

@router.get("/plants", response_model=List[ProductResponse])
def get_plants(
    category: Optional[str] = None,
    q: Optional[str] = None,
    include_inactive: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    return get_products(category=category, q=q, include_inactive=include_inactive, db=db)

@router.post("/plants/create", response_model=ProductResponse)
def create_plant_compat(
    payload: ProductCreate,
    db: Session = Depends(get_db)
):
    return create_product(payload=payload, db=db)

@router.put("/plants/update/{product_id}", response_model=ProductResponse)
def update_plant_compat(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db)
):
    return update_product(product_id=product_id, payload=payload, db=db)

@router.put("/plants/update", response_model=ProductResponse)
def update_plant_compat_query(
    payload: ProductUpdate,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    pid = product_id
    if pid is None and payload.id is not None:
        pid = payload.id
    if pid is None:
        raise HTTPException(status_code=400, detail="Product ID must be provided either as a query param or in the request body")
    return update_product(product_id=pid, payload=payload, db=db)

@router.delete("/plants/delete/{product_id}")
def delete_plant_compat_path(product_id: int, db: Session = Depends(get_db)):
    return delete_product(product_id=product_id, db=db)

@router.delete("/plants/delete")
def delete_plant_compat_query(product_id: int, db: Session = Depends(get_db)):
    return delete_product(product_id=product_id, db=db)

