from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database.connection import get_db
from models.interaction import Rating, Notification
from models.product import Product
from models.user import User
from models.order import Order
from schemas.interaction import RatingCreate, RatingResponse
from typing import List

router = APIRouter()

# --- ASYNC BROADCAST HELPER ---
async def broadcast_admin_notification(message: dict):
    from routers.notifications import manager
    await manager.broadcast(message)

@router.post("/products/{product_id}/ratings", response_model=RatingResponse)
def submit_rating(
    product_id: int,
    email: str,
    payload: RatingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Verify user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Verify product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Verify order is delivered
    order = db.query(Order).filter(Order.order_id == payload.order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=400, detail="Order not found for user")
    if order.status.lower() != "delivered":
        raise HTTPException(status_code=400, detail="Only delivered orders can be rated")
        
    # Create rating
    rating_rec = Rating(
        product_id=product_id,
        user_id=user.id,
        order_id=payload.order_id,
        rating=payload.rating,
        review=payload.review
    )
    db.add(rating_rec)
    db.flush()
    
    # Recalculate average rating for product
    ratings = db.query(Rating).filter(Rating.product_id == product_id).all()
    total_rating = sum(r.rating for r in ratings)
    count = len(ratings)
    
    product.rating = round(total_rating / count, 1)
    product.reviews_count = count
    
    # Create notification for admin
    notif = Notification(
        user_id=None,
        title="New Customer Feedback",
        message=f"Rating: {payload.rating} Stars",
        type="feedback"
    )
    db.add(notif)
    
    db.commit()
    
    # Broadcast to admins
    background_tasks.add_task(broadcast_admin_notification, {
        "title": notif.title,
        "message": notif.message,
        "type": notif.type,
        "product_id": product_id,
        "rating": payload.rating
    })
    
    return rating_rec

@router.get("/products/{product_id}/ratings", response_model=List[RatingResponse])
def get_product_ratings(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return db.query(Rating).filter(Rating.product_id == product_id).order_by(Rating.created_at.desc()).all()
