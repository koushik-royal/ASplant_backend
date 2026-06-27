import os
import shutil
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from database.connection import get_db
from models.order import Order, OrderItem, DeliveryTracking, DeliveryProof, Payment
from models.interaction import Notification, Rating
from models.user import User
from models.product import Product
from schemas.order import OrderCreate, OrderResponse, OrderUpdateStatus
from config import settings
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

# --- ORDER PLACEMENT ---

# --- ASYNC BROADCAST HELPER ---
async def broadcast_admin_notification(message: dict):
    from routers.notifications import manager
    await manager.broadcast(message)

@router.post("/orders", response_model=OrderResponse)
def place_order(email: str, payload: OrderCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Generate unique order id
    import random
    order_num = random.randint(10000, 99999)
    order_id = f"#PLT{order_num}"
    
    # Verify no collision
    while db.query(Order).filter(Order.order_id == order_id).first():
        order_num = random.randint(10000, 99999)
        order_id = f"#PLT{order_num}"
        
    current_date = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    
    # Determine payment status
    if payload.payment_method == "QR Payment":
        if payload.transaction_id:
            existing_payment = db.query(Payment).filter(
                Payment.transaction_id == payload.transaction_id,
                Payment.payment_method == "QR Payment"
            ).first()
            if existing_payment:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This Transaction ID / UTR number has already been used for another order payment."
                )
        payment_status = "Paid"
    elif payload.payment_method == "Cash on Delivery":
        payment_status = "Pending"
    else:
        payment_status = "UNPAID"
    
    # Create main order entry
    order = Order(
        order_id=order_id,
        user_id=user.id,
        date=current_date,
        status="Pending",
        subtotal=payload.subtotal,
        delivery_charge=payload.delivery_charge,
        total_amount=payload.total_amount,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        pincode=payload.pincode,
        address_line=payload.address_line,
        landmark=payload.landmark or "",
        city=payload.city,
        state=payload.state,
        district=payload.district or "",
        country=payload.country or "",
        address_type=payload.address_type or "HOME",
        delivery_option=payload.delivery_option or "Standard Delivery",
        payment_method=payload.payment_method,

        payment_status=payment_status,
        delivery_proof_path="",
        customer_signature_path=""
    )
    db.add(order)
    db.flush() # Secure the ID
    
    # Create order items and decrement stock
    calculated_subtotal = 0
    
    for item in payload.items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product with id {item.product_id} not found")
        
        # Check stock
        if prod.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {prod.name}")
        
        # Decrement stock
        prod.stock_quantity -= item.quantity
        
        # Low stock check
        if prod.stock_quantity <= 5:
            low_stock_notif = Notification(
                user_id=None,
                title="Low Stock Alert",
                message=f"{prod.name} remaining: {prod.stock_quantity}",
                type="stock"
            )
            db.add(low_stock_notif)
            background_tasks.add_task(broadcast_admin_notification, {
                "title": low_stock_notif.title,
                "message": low_stock_notif.message,
                "type": "low_stock",
                "product_id": prod.id,
                "remaining": prod.stock_quantity
            })
        
        # Calculate real price from database
        real_price = prod.price
        calculated_subtotal += real_price * item.quantity
        
        order_item = OrderItem(
            order_id=order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=real_price
        )
        db.add(order_item)
        
    # Update order with real calculated amounts
    order.subtotal = calculated_subtotal
    order.total_amount = calculated_subtotal + payload.delivery_charge
    db.add(order)
    
    # Log initial status change
    tracking = DeliveryTracking(
        order_id=order_id,
        status="Pending",
        remarks="Order placed successfully."
    )
    db.add(tracking)
    
    # Log payment status
    payment = Payment(
        order_id=order_id,
        user_id=user.id,
        payment_method=payload.payment_method,
        amount=order.total_amount,
        transaction_id=payload.transaction_id if payload.payment_method == "QR Payment" else "",
        status=payment_status,
        verified_at=datetime.datetime.now() if payment_status == "Paid" else None
    )
    db.add(payment)
    
    # Create notification for admin
    if payload.payment_method == "QR Payment":
        notif = Notification(
            user_id=None,
            title="New QR Payment Submitted",
            message=f"Order {order_id} placed by {user.name} for ₹{payload.total_amount}. (UTR: {payload.transaction_id})",
            type="payment"
        )
    else:
        notif = Notification(
            user_id=None,
            title="New Order Received",
            message=f"Order {order_id} placed by {user.name} for ₹{payload.total_amount}.",
            type="order"
        )
    db.add(notif)
    
    db.commit()
    
    # Broadcast to admins
    bg_message = {
        "title": notif.title,
        "message": notif.message,
        "type": notif.type,
        "order_id": order_id
    }
    background_tasks.add_task(broadcast_admin_notification, bg_message)
    
    # Return full order with items loaded
    return db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product)).filter(Order.order_id == order_id).first()

# --- RETRIEVALS ---

@router.get("/orders", response_model=List[OrderResponse])
def get_orders(email: str, role: Optional[str] = "customer", db: Session = Depends(get_db)):
    if role == "admin":
        orders = db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images)).order_by(Order.id.desc()).all()
    else:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        orders = db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images)).filter(Order.user_id == user.id).order_by(Order.id.desc()).all()

    order_ids = [o.order_id for o in orders]
    if order_ids:
        ratings = db.query(Rating).filter(Rating.order_id.in_(order_ids)).all()
        rated_set = {(r.order_id, r.product_id) for r in ratings}
        for o in orders:
            for item in o.items:
                item.is_rated = (o.order_id, item.product_id) in rated_set

    return orders

@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_by_id(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images)).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    ratings = db.query(Rating).filter(Rating.order_id == order_id).all()
    rated_set = {r.product_id for r in ratings}
    for item in order.items:
        item.is_rated = item.product_id in rated_set

    return order

# --- STATUS UPDATES ---

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: str, payload: OrderUpdateStatus, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    old_status = order.status
    order.status = payload.status
    
    # Automatically set payment status to Paid for Cash on Delivery when delivered
    if payload.status == "Delivered":
        if order.payment_method == "Cash on Delivery":
            order.payment_status = "Paid"
            payment = db.query(Payment).filter(Payment.order_id == order_id).first()
            if payment:
                payment.status = "Paid"
                payment.verified_at = datetime.datetime.now()

    # Log status change
    tracking = DeliveryTracking(
        order_id=order_id,
        status=payload.status,
        remarks=f"Order status changed to {payload.status}."
    )
    db.add(tracking)

    # Notify the customer about the status change
    status_messages = {
        "Confirmed":  ("Order Confirmed! 🎉", f"Your order {order_id} has been confirmed and is being prepared."),
        "Packed":     ("Order Packed 📦", f"Your order {order_id} has been packed and is ready to ship."),
        "Processing": ("Order Processing ⚙️", f"Your order {order_id} is currently being processed."),
        "Shipped":    ("Order Shipped 🚚", f"Your order {order_id} is on its way! Track your delivery soon."),
        "Delivered":  ("Order Delivered ✅", f"Your order {order_id} has been delivered. Enjoy your plants!"),
        "Cancelled":  ("Order Cancelled ❌", f"Your order {order_id} has been cancelled. Contact support if this was unexpected."),
    }
    if payload.status in status_messages and order.user_id:
        title, message = status_messages[payload.status]
        notif = Notification(
            user_id=order.user_id,
            title=title,
            message=message,
            type="order",
            is_read=False,
        )
        db.add(notif)

    db.commit()
    
    if payload.status == "Cancelled":
        background_tasks.add_task(broadcast_admin_notification, {
            "title": "Order Cancelled",
            "message": f"Order {order_id} has been cancelled.",
            "type": "order_cancelled",
            "order_id": order_id
        })

    return {"status": "success", "message": f"Order status updated to {payload.status}"}

# --- PAYMENT SCREENSHOT UPLOADER ---

@router.post("/orders/{order_id}/payment")
def upload_payment_screenshot(
    order_id: str,
    transaction_id: Optional[str] = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if transaction_id and order.payment_method == "QR Payment":
        existing_payment = db.query(Payment).filter(
            Payment.transaction_id == transaction_id,
            Payment.order_id != order_id,
            Payment.payment_method == "QR Payment"
        ).first()
        if existing_payment:
            raise HTTPException(
                status_code=400,
                detail="This Transaction ID / UTR number has already been used for another order payment."
            )

    # Find payment record
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        payment = Payment(order_id=order_id, user_id=order.user_id, payment_method=order.payment_method, amount=order.total_amount)
        db.add(payment)
        
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"pay_{order_id.replace('#', '')}{file_ext}"
    filepath = os.path.join(settings.PAYMENT_UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url_path = f"{settings.SERVER_BASE_URL}/{settings.PAYMENT_UPLOAD_DIR}/{filename}"
    payment.screenshot_path = url_path
    payment.transaction_id = transaction_id
    if order.payment_method == "QR Payment":
        payment.status = "Paid"
        order.payment_status = "Paid"
        payment.verified_at = datetime.datetime.now()
    else:
        payment.status = "UNPAID"
    
    db.commit()
    return {"status": "success", "screenshot_url": url_path, "message": "Screenshot uploaded successfully."}

# --- PAYMENT VERIFICATION ---

@router.post("/orders/{order_id}/verify-payment")
def verify_payment(order_id: str, admin_email: str, background_tasks: BackgroundTasks, status: str = "Paid", db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
        
    payment.status = status
    if status == "Paid":
        payment.verified_at = datetime.datetime.now()
    else:
        payment.verified_at = None
        
    # Update order status
    order.payment_status = status
    
    db.commit()
    
    if status == "Paid":
        background_tasks.add_task(broadcast_admin_notification, {
            "title": "Payment Verified",
            "message": f"Payment for order {order_id} has been verified.",
            "type": "payment_verified",
            "order_id": order_id
        })

    return {"status": "success", "message": f"Order payment verified and marked as {status}"}

# --- DELIVERY PROOF & SIGNATURE UPLOADER ---

@router.post("/orders/{order_id}/delivery-proof")
def upload_delivery_proof(
    order_id: str,
    proof_image: UploadFile = File(...),
    signature_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Save proof image
    proof_ext = os.path.splitext(proof_image.filename)[1]
    proof_filename = f"proof_{order_id.replace('#', '')}{proof_ext}"
    proof_filepath = os.path.join(settings.PROOF_UPLOAD_DIR, proof_filename)
    with open(proof_filepath, "wb") as buffer:
        shutil.copyfileobj(proof_image.file, buffer)
    proof_url = f"{settings.SERVER_BASE_URL}/{settings.PROOF_UPLOAD_DIR}/{proof_filename}"
    
    # Save signature image
    sig_ext = os.path.splitext(signature_image.filename)[1]
    sig_filename = f"sig_{order_id.replace('#', '')}{sig_ext}"
    sig_filepath = os.path.join(settings.SIGNATURE_UPLOAD_DIR, sig_filename)
    with open(sig_filepath, "wb") as buffer:
        shutil.copyfileobj(signature_image.file, buffer)
    sig_url = f"{settings.SERVER_BASE_URL}/{settings.SIGNATURE_UPLOAD_DIR}/{sig_filename}"
    
    # Save to delivery_proof table
    proof_rec = DeliveryProof(
        order_id=order_id,
        image_path=proof_url,
        signature_path=sig_url
    )
    db.add(proof_rec)
    
    # Update order fields
    order.delivery_proof_path = proof_url
    order.customer_signature_path = sig_url
    order.status = "Delivered"
    
    # Automatically set payment status to Paid for Cash on Delivery when delivered
    if order.payment_method == "Cash on Delivery":
        order.payment_status = "Paid"
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = "Paid"
            payment.verified_at = datetime.datetime.now()

    # Add status tracking log
    tracking = DeliveryTracking(
        order_id=order_id,
        status="Delivered",
        remarks="Order delivered. Proof of delivery uploaded."
    )
    db.add(tracking)
    
    db.commit()
    return {
        "status": "success",
        "message": "Delivery completed successfully.",
        "delivery_proof_path": proof_url,
        "customer_signature_path": sig_url
    }

# --- TRACKING HISTORY ---

@router.get("/orders/{order_id}/tracking")
def get_order_tracking(order_id: str, db: Session = Depends(get_db)):
    logs = db.query(DeliveryTracking).filter(DeliveryTracking.order_id == order_id).order_by(DeliveryTracking.timestamp.asc()).all()
    return logs
