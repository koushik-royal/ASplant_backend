from database.connection import SessionLocal
from sqlalchemy import text

db = SessionLocal()
conn = db.bind.connect()

# Fix the plant - set a real price and restore to active
conn.execute(text("UPDATE plants SET price = 299, status = 'active', is_active = 1 WHERE id = 67"))

# Fix the order amounts (subtotal + delivery = total)
conn.execute(text("UPDATE orders SET subtotal = 299, total_amount = 349, delivery_charge = 50 WHERE order_number = '#PLT89524'"))

# Fix the order item price to match plant price
conn.execute(text("UPDATE order_items SET price = 299 WHERE order_id = '#PLT89524'"))

# Fix payment record to match order total
try:
    conn.execute(text("UPDATE payments SET amount = 349 WHERE order_id = '#PLT89524'"))
except Exception as e:
    print(f"Payment update skipped: {e}")

conn.commit()
conn.close()
db.close()
print("Fixed: plant price=299, order total=349, delivery=50")

# Verify
db2 = SessionLocal()
conn2 = db2.bind.connect()
result = conn2.execute(text("SELECT order_number, order_status, total_amount, subtotal, delivery_charge FROM orders"))
for row in result.fetchall():
    print("Order:", row)
result2 = conn2.execute(text("SELECT id, name, price, status FROM plants"))
for row in result2.fetchall():
    print("Plant:", row)
conn2.close()
db2.close()
