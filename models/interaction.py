from sqlalchemy import Column, Integer, String, Double, Text, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from database.connection import Base

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column("plant_id", Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)

    product = relationship("Product")

class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column("plant_id", Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1)

    product = relationship("Product")

class Rating(Base):
    __tablename__ = "plant_ratings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column("plant_id", Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(String(50), ForeignKey("orders.order_number", ondelete="CASCADE"), nullable=False)
    rating = Column(Double, nullable=False)
    review = Column(Text)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    product = relationship("Product", back_populates="ratings")
    user = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False) # "order", "stock", "payout", "system"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
