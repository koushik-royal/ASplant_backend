import os
import shutil
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query, Header
from sqlalchemy.orm import Session, joinedload
from database.connection import get_db
from models.order import Order, OrderItem, DeliveryTracking, DeliveryProof, Payment
from models.interaction import Notification, Rating
from models.user import User, Admin
from models.product import Product
from models.setting import StoreSetting
from schemas.order import OrderCreate, OrderResponse, OrderUpdateStatus
from config import settings
from services.storage_service import storage_service
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

# --- ORDER PLACEMENT ---

# --- ASYNC BROADCAST HELPER ---
async def broadcast_admin_notification(message: dict):
    from routers.notifications import manager
    from services.fcm import send_push_notification_to_all_admins
    await manager.broadcast(message)
    # Also trigger FCM push notification to all admins
    title = message.get("title", "Plantora Admin")
    body = message.get("message", "")
    notif_type = message.get("type", "system")
    send_push_notification_to_all_admins(title, body, notif_type)

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
    store_setting = db.query(StoreSetting).filter(StoreSetting.id == 1).first()
    low_stock_threshold = store_setting.low_stock_threshold if store_setting else 5
    
    for item in payload.items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product with id {item.product_id} not found")
        
        # Check stock
        if prod.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {prod.name}")
        
        # Decrement stock
        old_stock = prod.stock_quantity
        prod.stock_quantity -= item.quantity
        
        # Low stock check (trigger ONLY when crossing the threshold downwards)
        if old_stock > low_stock_threshold and prod.stock_quantity <= low_stock_threshold:
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
        orders = db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.category)
        ).order_by(Order.id.desc()).all()
    else:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        orders = db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images),
            joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.category)
        ).filter(Order.user_id == user.id).order_by(Order.id.desc()).all()

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
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.images),
        joinedload(Order.items).joinedload(OrderItem.product).joinedload(Product.category)
    ).filter(Order.order_id == order_id).first()
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
        
        # Trigger FCM push notification to the customer
        from services.fcm import send_push_notification
        user = db.query(User).filter(User.id == order.user_id).first()
        if user:
            send_push_notification(user.email, title, message, "order", "customer")

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
        
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"pay_{order_id.replace('#', '')}{file_ext}"
    url_path = storage_service.upload_image(file.file, filename, folder="payments")
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
    proof_ext = os.path.splitext(proof_image.filename)[1] or ".jpg"
    proof_filename = f"proof_{order_id.replace('#', '')}{proof_ext}"
    proof_url = storage_service.upload_image(proof_image.file, proof_filename, folder="proofs")
    
    # Save signature image
    sig_ext = os.path.splitext(signature_image.filename)[1] or ".png"
    sig_filename = f"sig_{order_id.replace('#', '')}{sig_ext}"
    sig_url = storage_service.upload_image(signature_image.file, sig_filename, folder="signatures")
    
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

# --- ORDER DELETION (ADMIN ONLY) ---

@router.delete("/orders/{order_id}")
def delete_order(
    order_id: str,
    admin_email: Optional[str] = Query(None, description="Admin email for authorization"),
    x_admin_email: Optional[str] = Header(None, alias="X-Admin-Email", description="Admin email header for authorization"),
    db: Session = Depends(get_db)
):
    """
    Safely and permanently deletes an order and all its associated records:
    - Verifies admin privileges.
    - Removes related notifications.
    - Removes ratings, delivery proof, delivery tracking, payment, and order items.
    - Removes the parent order record.
    - Cleans up Cloudinary or local storage files associated with proof/signature/payment screenshots.
    - Uses an atomic transaction that rolls back on any error.
    """
    # 1. Admin authorization check
    email = (admin_email or x_admin_email or "").strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin email is required to authorize order deletion."
        )

    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only registered administrators can delete orders."
        )

    # 2. Locate the order (handles both '#PLT12345' and 'PLT12345')
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order and not order_id.startswith("#"):
        order = db.query(Order).filter(Order.order_id == f"#{order_id}").first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found."
        )

    target_order_id = order.order_id

    # 3. Collect associated storage file paths/URLs to delete after successful DB commit
    files_to_delete = set()
    if order.delivery_proof_path:
        files_to_delete.add(order.delivery_proof_path)
    if order.customer_signature_path:
        files_to_delete.add(order.customer_signature_path)

    proof_records = db.query(DeliveryProof).filter(DeliveryProof.order_id == target_order_id).all()
    for proof in proof_records:
        if proof.image_path:
            files_to_delete.add(proof.image_path)
        if proof.signature_path:
            files_to_delete.add(proof.signature_path)

    payment_records = db.query(Payment).filter(Payment.order_id == target_order_id).all()
    for pay in payment_records:
        if pay.screenshot_path:
            files_to_delete.add(pay.screenshot_path)

    # 4. Atomic database transaction
    try:
        # 4a. Delete related notifications (notifications table has no FK to orders)
        deleted_notifs = db.query(Notification).filter(
            (Notification.message.like(f"%{target_order_id}%")) |
            (Notification.title.like(f"%{target_order_id}%"))
        ).delete(synchronize_session=False)

        # 4b. Delete plant ratings associated with this order
        db.query(Rating).filter(Rating.order_id == target_order_id).delete(synchronize_session=False)

        # 4c. Delete delivery proofs
        db.query(DeliveryProof).filter(DeliveryProof.order_id == target_order_id).delete(synchronize_session=False)

        # 4d. Delete delivery tracking history
        db.query(DeliveryTracking).filter(DeliveryTracking.order_id == target_order_id).delete(synchronize_session=False)

        # 4e. Delete payment records
        db.query(Payment).filter(Payment.order_id == target_order_id).delete(synchronize_session=False)

        # 4f. Delete order items
        db.query(OrderItem).filter(OrderItem.order_id == target_order_id).delete(synchronize_session=False)

        # 4g. Delete the parent order
        db.delete(order)

        # Commit all changes atomically
        db.commit()

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete order {target_order_id}: {str(exc)}"
        )

    # 5. Clean up Cloudinary / local storage files safely after DB commit
    for file_url in files_to_delete:
        try:
            storage_service.delete_image(file_url)
        except Exception as file_err:
            print(f"[STORAGE] Warning: Failed to clean up file '{file_url}': {file_err}")

    return {
        "status": "success",
        "message": f"Order {target_order_id} and all related records have been permanently deleted.",
        "order_id": target_order_id,
        "notifications_removed": deleted_notifs
    }
