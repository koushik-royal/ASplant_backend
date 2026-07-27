from sqlalchemy import Column, Integer, String, Boolean, DateTime, text
from database.connection import Base

class PaymentSetting(Base):
    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)
    cod_enabled = Column(Boolean, default=True)
    bank_name = Column(String(100))
    account_number = Column(String(50))
    ifsc_code = Column(String(20))
    account_holder = Column(String(100))
    express_delivery_charge = Column(Integer, default=79)

class QrCode(Base):
    __tablename__ = "qr_payment"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column("account_name", String(50), nullable=False)
    upi_id = Column(String(100), nullable=False)
    account_holder = Column(String(100), default="AS Plants Admin")
    image_path = Column("qr_image", String(255), default="")
    is_active = Column("active", Boolean, default=True)
    updated_by_admin = Column(Integer, default=1)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class DeliverySetting(Base):
    __tablename__ = "delivery_settings"

    id = Column(Integer, primary_key=True, index=True)
    standard_name = Column(String(100), default="Standard Delivery")
    standard_days = Column(String(50), default="3-5 days")
    standard_price = Column(Integer, default=0)
    express_name = Column(String(100), default="Express Delivery")
    express_days = Column(String(50), default="1-2 days")
    express_price = Column(Integer, default=79)

class StoreSetting(Base):
    __tablename__ = "store_settings"

    id = Column(Integer, primary_key=True, index=True)
    low_stock_threshold = Column(Integer, default=5)

