"""
Fix existing image URLs in database that have hardcoded 10.0.2.2 emulator IP.
Run this once: python fix_image_urls.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from models.product import Product, ProductImage, Category
from models.user import User, Admin
from models.interaction import Notification
from sqlalchemy import text
from config import settings

OLD_HOST = "http://10.0.2.2:8000"
NEW_HOST = settings.SERVER_BASE_URL.rstrip("/")

def fix_urls(db):
    total_fixed = 0

    # Fix ProductImage.image_path
    images = db.query(ProductImage).filter(ProductImage.image_path.like(f"{OLD_HOST}%")).all()
    for img in images:
        img.image_path = img.image_path.replace(OLD_HOST, NEW_HOST)
        total_fixed += 1
    print(f"Fixed {len(images)} ProductImage rows")

    # Fix Product.image_url
    products = db.query(Product).filter(Product.image_url.like(f"{OLD_HOST}%")).all()
    for p in products:
        p.image_url = p.image_url.replace(OLD_HOST, NEW_HOST)
        total_fixed += 1
    print(f"Fixed {len(products)} Product.image_url rows")

    # Fix Category.image_url
    categories = db.query(Category).filter(Category.image_url.like(f"{OLD_HOST}%")).all()
    for c in categories:
        c.image_url = c.image_url.replace(OLD_HOST, NEW_HOST)
        total_fixed += 1
    print(f"Fixed {len(categories)} Category.image_url rows")

    # Fix Admin.profile_image
    try:
        admins = db.query(Admin).filter(Admin.profile_image.like(f"{OLD_HOST}%")).all()
        for a in admins:
            a.profile_image = a.profile_image.replace(OLD_HOST, NEW_HOST)
            total_fixed += 1
        print(f"Fixed {len(admins)} Admin.profile_image rows")
    except Exception as e:
        print(f"Skipping Admin (table may differ): {e}")

    # Fix User.profile_image
    try:
        users = db.query(User).filter(User.profile_image.like(f"{OLD_HOST}%")).all()
        for u in users:
            u.profile_image = u.profile_image.replace(OLD_HOST, NEW_HOST)
            total_fixed += 1
        print(f"Fixed {len(users)} User.profile_image rows")
    except Exception as e:
        print(f"Skipping User: {e}")

    db.commit()
    print(f"\n✅ Total fixed: {total_fixed} rows")
    print(f"   Old: {OLD_HOST}")
    print(f"   New: {NEW_HOST}")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        fix_urls(db)
    finally:
        db.close()
