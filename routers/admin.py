from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database.connection import get_db
from models.order import Order, OrderItem, Payment
from models.user import User
from models.product import Product
from schemas.order import OrderResponse
from typing import List, Dict, Any

router = APIRouter()

@router.get("/admin/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    # 1. Total Orders
    total_orders = db.query(Order).count()
    
    # 2. Total Customers (registered users)
    total_customers = db.query(User).count()
    
    # 3. Total Products
    total_products = db.query(Product).filter(Product.is_active == True).count()
    
    # 4. Total Revenue (sum of total_amount of delivered or confirmed or paid orders)
    # Revenue must use real paid orders. Sum orders.total_amount where payment_status='Paid'.
    revenue_query = db.query(Order).filter(Order.payment_status.ilike('paid')).all()
    total_revenue = sum(o.total_amount for o in revenue_query)
    
    # 5. Payment Statistics (Count of paid vs unpaid)
    payments = db.query(Payment).all()
    paid_count = sum(1 for p in payments if p.status == "PAID")
    unpaid_count = sum(1 for p in payments if p.status == "UNPAID")
    
    # Break down by payment method
    methods = {}
    for p in payments:
        methods[p.payment_method] = methods.get(p.payment_method, 0) + p.amount
        
    payment_stats = {
        "paid_orders": paid_count,
        "unpaid_orders": unpaid_count,
        "revenue_by_method": methods
    }
    
    # 6. Recent Orders (limit 5)
    recent = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product)
    ).order_by(Order.id.desc()).limit(5).all()
    
    # Convert to response objects
    recent_responses = []
    for o in recent:
        # Map manually or rely on pydantic
        items_list = []
        for item in o.items:
            items_list.append({
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "plant": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "category_id": item.product.category_id,
                    "rating": getattr(item.product, "rating", 0.0),
                    "reviews_count": getattr(item.product, "reviews_count", 0),
                    "image_paths": [img.image_path for img in item.product.images] if item.product and hasattr(item.product, 'images') else []
                } if item.product else None
            })
            
        recent_responses.append({
            "id": o.id,
            "order_id": o.order_id,
            "user_id": o.user_id,
            "date": o.date,
            "status": o.status,
            "subtotal": o.subtotal,
            "delivery_charge": o.delivery_charge,
            "total_amount": o.total_amount,
            "full_name": o.full_name,
            "phone_number": o.phone_number,
            "pincode": o.pincode,
            "address_line": o.address_line,
            "landmark": o.landmark,
            "city": o.city,
            "state": o.state,
            "address_type": o.address_type,
            "delivery_option": o.delivery_option,
            "payment_method": o.payment_method,
            "delivery_proof_path": o.delivery_proof_path,
            "customer_signature_path": o.customer_signature_path,
            "items": items_list
        })
        
    # 7. Generate Chart Data
    import datetime
    today = datetime.datetime.now()
    labels = []
    points = []
    for i in range(4, -1, -1):
        target = today - datetime.timedelta(days=i * 7)
        labels.append(f"{target.day} {target.strftime('%b')}")
        points.append(total_revenue / 5) # simplified mock points based on revenue
        
    chart_data = {
        "labels": labels,
        "points": points
    }

    return {
        "status": "success",
        "stats": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "total_products": total_products,
            "payment_statistics": payment_stats,
            "chart_data": chart_data
        },
        "recent_orders": recent_responses
    }

@router.get("/admin/customers")
def get_admin_customers(db: Session = Depends(get_db)):
    customers = db.query(User).all()
    res = []
    for c in customers:
        created_str = c.created_at.strftime("%d %b %Y") if c.created_at else ""
        res.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone or "",
            "profile_image": c.profile_image or "",
            "created_at": created_str
        })
    return res
