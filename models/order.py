from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from database.connection import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column("order_number", String(50), unique=True, nullable=False, index=True)
    user_id = Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(100), nullable=False)
    status = Column("order_status", String(50), default="Pending")
    subtotal = Column(Integer, nullable=False)
    delivery_charge = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    pincode = Column(String(20), nullable=False)
    address_line = Column(String(255), nullable=False)
    landmark = Column(String(100), default="")
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100))
    country = Column(String(100))
    address_type = Column(String(20), default="HOME")
    

    delivery_option = Column("delivery_type", String(50), default="Standard Delivery")
    payment_method = Column(String(50), nullable=False)
    delivery_proof_path = Column(String(255), default="")
    customer_signature_path = Column(String(255), default="")
    
    # User exact specs
    payment_status = Column("payment_status", String(50), default="UNPAID")
    created_at = Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP"))

    @property
    def screenshot_path(self):
        return self.payments[0].screenshot_path if self.payments else ""

    @property
    def transaction_id(self):
        return self.payments[0].transaction_id if self.payments else ""

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tracking = relationship("DeliveryTracking", back_populates="order", cascade="all, delete-orphan")
    proofs = relationship("DeliveryProof", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_number", ondelete="CASCADE"), nullable=False)
    product_id = Column("plant_id", Integer, ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    @property
    def plant(self):
        return self.product


class DeliveryTracking(Base):
    __tablename__ = "delivery_tracking"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_number", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    remarks = Column(String(255), default="")

    order = relationship("Order", back_populates="tracking")

class DeliveryProof(Base):
    __tablename__ = "delivery_proof"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_number", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(255), nullable=False)
    signature_path = Column(String(255), nullable=False)
    verified_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    order = relationship("Order", back_populates="proofs")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_number", ondelete="CASCADE"), nullable=False)
    user_id = Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_id = Column(String(100), default="")
    status = Column(String(50), default="UNPAID")
    screenshot_path = Column(String(255), default="")
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, nullable=True)

    order = relationship("Order", back_populates="payments")
