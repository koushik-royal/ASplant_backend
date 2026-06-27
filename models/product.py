from sqlalchemy import Column, Integer, String, Double, Text, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from database.connection import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    image_url = Column(String(255), default="")

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column("plant_name", String(100), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    price = Column(Integer, nullable=False)
    rating = Column(Double, default=0.0)
    reviews_count = Column(Integer, default=0)
    description = Column(Text)
    benefits = Column(String(255))
    watering = Column(String(100))
    sunlight = Column(String(100))
    pot_size = Column(String(100))
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    stock_quantity = Column("stock", Integer, default=25)
    height = Column(String(50), default="30cm")
    weight = Column(String(50), default="1.2kg")
    is_featured = Column(Boolean, default=False)
    detailed_description = Column(Text, default="")
    
    # Custom fields for user database specs
    admin_id = Column(Integer, default=1)
    category_name = Column("category", String(100), default="Indoor")
    image_url = Column(String(255), default="")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="product", cascade="all, delete-orphan")

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(255), nullable=False)
    display_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")
