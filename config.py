import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env", override=True)
elif os.path.exists("env.txt"):
    load_dotenv("env.txt", override=True)
else:
    load_dotenv(override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "AS Plants API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/plantora")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "plantora_super_secret_key_12345")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 # 30 days session
    
    # Server base URL — set this to your machine's LAN IP for real device testing
    # e.g. export SERVER_BASE_URL=http://192.168.1.20:8000
    SERVER_BASE_URL: str = os.getenv("SERVER_BASE_URL", "http://192.168.1.20:8000")
    
    # Upload folder paths
    UPLOAD_DIR: str = "uploads"
    PROFILE_UPLOAD_DIR: str = "uploads/profiles"
    PROFILE_IMAGES_DIR: str = "uploads/profile_images"
    PRODUCT_UPLOAD_DIR: str = "uploads/products"
    PAYMENT_UPLOAD_DIR: str = "uploads/payments"
    QR_UPLOAD_DIR: str = "uploads/qr_codes"
    PROOF_UPLOAD_DIR: str = "uploads/proofs"
    SIGNATURE_UPLOAD_DIR: str = "uploads/signatures"

    # SMTP Settings
    SMTP_SERVER: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_SENDER: str = os.getenv("SMTP_USERNAME", os.getenv("SMTP_SENDER", ""))
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_DISPLAY_NAME: str = os.getenv("SMTP_DISPLAY_NAME", "AS Plants")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure directories exist
for folder in [
    settings.UPLOAD_DIR,
    settings.PROFILE_UPLOAD_DIR,
    settings.PROFILE_IMAGES_DIR,
    settings.PRODUCT_UPLOAD_DIR,
    settings.PAYMENT_UPLOAD_DIR,
    settings.QR_UPLOAD_DIR,
    settings.PROOF_UPLOAD_DIR,
    settings.SIGNATURE_UPLOAD_DIR
]:
    os.makedirs(folder, exist_ok=True)

# Hot-reload trigger: SMTP credentials updated, triggering reload. Force reload 1.
