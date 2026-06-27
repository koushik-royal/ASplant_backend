from database.connection import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    conn = db.bind.connect()
    # List all tables
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result.fetchall()]
    print(f"Tables in database: {tables}")
    
    for table in tables:
        count_res = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
        count = count_res.fetchone()[0]
        print(f"Table: {table:25} | Row Count: {count}")
        
    print("\n--- Orders Detail ---")
    result = conn.execute(text("SELECT id, order_number, customer_id, date, order_status, total_amount, full_name FROM orders"))
    for row in result.fetchall():
        print(f"ID: {row[0]} | OrderNumber: {row[1]} | CustomerID: {row[2]} | Date: {row[3]} | Status: {row[4]} | Amount: {row[5]} | Name: {row[6]}")

    print("\n--- Order Items Detail ---")
    if "order_items" in tables:
        result = conn.execute(text("SELECT id, order_id, plant_id, quantity, price FROM order_items"))
        for row in result.fetchall():
            print(f"ID: {row[0]} | OrderID: {row[1]} | PlantID: {row[2]} | Qty: {row[3]} | Price: {row[4]}")
            
    print("\n--- Plants Detail ---")
    if "plants" in tables:
        result = conn.execute(text("SELECT id, plant_name, price, stock, is_active, status FROM plants"))
        for row in result.fetchall():
            print(f"ID: {row[0]} | Name: {row[1]} | Price: {row[2]} | Stock: {row[3]} | Active: {row[4]} | Status: {row[5]}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
