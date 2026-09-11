import sys
from database.connection import engine
# pyrefly: ignore [missing-import]
from sqlalchemy import text

try:
    with engine.connect() as conn:
        print("Adding fcm_token to customers...")
        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN fcm_token VARCHAR(255) DEFAULT NULL;"))
            print("Added to customers")
        except Exception as e:
            print(f"customers error (maybe already exists): {e}")

        print("Adding fcm_token to admins...")
        try:
            conn.execute(text("ALTER TABLE admins ADD COLUMN fcm_token VARCHAR(255) DEFAULT NULL;"))
            print("Added to admins")
        except Exception as e:
            print(f"admins error: {e}")

        print("Adding deleted to notifications...")
        try:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN deleted BOOLEAN DEFAULT 0;"))
            print("Added to notifications")
        except Exception as e:
            print(f"notifications error: {e}")
        
        conn.commit()
    print("Done")
except Exception as e:
    print(f"Fatal error: {e}")
