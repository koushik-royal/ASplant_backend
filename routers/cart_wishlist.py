from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from database.connection import get_db
from models.interaction import Cart, Wishlist
from models.user import User
from models.product import Product
from schemas.interaction import CartCreate, CartUpdate, CartResponse, WishlistToggle, WishlistResponse
from typing import List

router = APIRouter()

# Helper to get user by email
def get_user_by_email(email: str, db: Session) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# --- CART ENDPOINTS ---

@router.get("/cart", response_model=List[CartResponse])
def get_cart(email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    return db.query(Cart).options(joinedload(Cart.product)).filter(Cart.user_id == user.id).all()

@router.post("/cart/add", response_model=CartResponse)
def add_to_cart(email: str, payload: CartCreate, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    # Check product
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.status == "deleted":
        raise HTTPException(status_code=400, detail="Product is no longer available")
        
    db_cart = db.query(Cart).filter(Cart.user_id == user.id, Cart.product_id == payload.product_id).first()
    if db_cart:
        db_cart.quantity += payload.quantity
    else:
        db_cart = Cart(user_id=user.id, product_id=payload.product_id, quantity=payload.quantity)
        db.add(db_cart)
        
    db.commit()
    db.refresh(db_cart)
    
    # Reload with joined product
    return db.query(Cart).options(joinedload(Cart.product)).filter(Cart.id == db_cart.id).first()

@router.put("/cart/update", response_model=CartResponse)
def update_cart_quantity(email: str, product_id: int, payload: CartUpdate, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    db_cart = db.query(Cart).filter(Cart.user_id == user.id, Cart.product_id == product_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart item not found")
        
    if payload.quantity <= 0:
        db.delete(db_cart)
        db.commit()
        return {"status": "success", "message": "Item removed from cart"}
        
    db_cart.quantity = payload.quantity
    db.commit()
    db.refresh(db_cart)
    return db.query(Cart).options(joinedload(Cart.product)).filter(Cart.id == db_cart.id).first()

@router.delete("/cart/remove")
def remove_from_cart(email: str, product_id: int, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    db_cart = db.query(Cart).filter(Cart.user_id == user.id, Cart.product_id == product_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart item not found")
        
    db.delete(db_cart)
    db.commit()
    return {"status": "success", "message": "Item removed from cart"}

@router.delete("/cart/clear")
def clear_cart(email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    db.query(Cart).filter(Cart.user_id == user.id).delete()
    db.commit()
    return {"status": "success", "message": "Cart cleared"}


# --- WISHLIST ENDPOINTS ---

@router.get("/wishlist", response_model=List[WishlistResponse])
def get_wishlist(email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    return db.query(Wishlist).options(joinedload(Wishlist.product)).filter(Wishlist.user_id == user.id).all()

@router.post("/wishlist/toggle")
def toggle_wishlist(email: str, payload: WishlistToggle, db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    
    db_wish = db.query(Wishlist).filter(Wishlist.user_id == user.id, Wishlist.product_id == payload.product_id).first()
    if db_wish:
        db.delete(db_wish)
        db.commit()
        return {"status": "success", "in_wishlist": False, "message": "Removed from wishlist"}
    else:
        # Block adding soft-deleted products to wishlist
        product = db.query(Product).filter(Product.id == payload.product_id).first()
        if not product or product.status == "deleted":
            raise HTTPException(status_code=400, detail="Product is no longer available")
        db_wish = Wishlist(user_id=user.id, product_id=payload.product_id)
        db.add(db_wish)
        db.commit()
        return {"status": "success", "in_wishlist": True, "message": "Added to wishlist"}
