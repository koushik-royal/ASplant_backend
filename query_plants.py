import models.interaction
import models.order
import models.setting
import models.user
from database.connection import SessionLocal
from models.product import Product

db = SessionLocal()
try:
    plants = db.query(Product).all()
    print(f"Total plants in DB: {len(plants)}")
    for p in plants:
        print(f"ID: {p.id}, Name: {p.name}, Category: {p.category_name}, Price: {p.price}, Status: {p.status}")
finally:
    db.close()
