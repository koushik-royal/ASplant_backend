from database.connection import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    conn = db.bind.connect()
    
    print("==================================================")
    print("              DATABASE PLANTS ROWS                ")
    print("==================================================")
    result = conn.execute(text("SELECT id, plant_name, price, stock, is_active, image_url FROM plants"))
    rows = result.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Name: {row[1]} | Price: {row[2]} | Stock: {row[3]} | Active: {row[4]} | Image: {row[5]}")
        
    print("\n==================================================")
    print("              DATABASE ADMINS ROWS                ")
    print("==================================================")
    result = conn.execute(text("SELECT id, name, email, phone, role FROM admins"))
    rows = result.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Name: {row[1]} | Email: {row[2]} | Phone: {row[3]} | Role: {row[4]}")
        
    print("\n==================================================")
    print("             DATABASE CUSTOMERS ROWS              ")
    print("==================================================")
    result = conn.execute(text("SELECT id, name, email, phone FROM customers"))
    rows = result.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Name: {row[1]} | Email: {row[2]} | Phone: {row[3]}")
    print("==================================================")

    conn.close()
except Exception as e:
    print(f"Error querying database: {e}")
finally:
    db.close()
