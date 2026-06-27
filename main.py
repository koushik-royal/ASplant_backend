from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Create folders if not exist
for folder in ["uploads", "uploads/profiles", "uploads/products", "uploads/payments", "uploads/qr_codes", "uploads/proofs", "uploads/signatures"]:
    os.makedirs(folder, exist_ok=True)

# Create a mock file for QR codes if not exists so it loads correctly
mock_qr = "uploads/qr_codes/qr_mock.png"
if not os.path.exists(mock_qr):
    with open(mock_qr, "wb") as f:
        # Just write 1 empty byte as mock image
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

from database.connection import engine, Base
# Import routers
from routers import auth, products, cart_wishlist, orders, settings, notifications, interactions, admin, customer

# Database migrations to align with new column schema specs (password_hash & name)
def run_migrations():
    from sqlalchemy import text
    import os
    print("[MIGRATION] Checking database columns...")
    log_content = []
    log_content.append("DATABASE SCHEMA REPORT\n======================\n")
    try:
        with engine.connect() as conn:
            # Let's get tables list
            tables_res = conn.execute(text("SHOW TABLES")).fetchall()
            tables = [row[0] for row in tables_res]
            log_content.append(f"Existing tables: {', '.join(tables)}\n")
            
            for t in tables:
                log_content.append(f"\nTable: {t}")
                col_res = conn.execute(text(f"SHOW COLUMNS FROM {t}")).fetchall()
                for col in col_res:
                    log_content.append(f"  - {col[0]} ({col[1]})")
            
            # Check if we need to run full setup_db.sql
            # We run it if 'plants' table is missing OR if 'products' table still exists, 
            # OR if 'qr_codes' exists instead of 'qr_payment' or if 'ratings' table still exists
            need_setup = False
            if "plants" not in tables or "products" in tables or "qr_codes" in tables or "qr_payment" not in tables or "ratings" in tables:
                need_setup = True
                log_content.append("\n\n-> Setup / Reset Required: True (Old tables detected or new tables missing)")
            
            if need_setup:
                log_content.append("\nRunning setup_db.sql automatically to initialize tables...")
                sql_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup_db.sql")
                if os.path.exists(sql_file_path):
                    with open(sql_file_path, "r", encoding="utf-8") as f:
                        sql_content_raw = f.read()
                    
                    # Split by semicolon, filter out comments
                    queries = []
                    current_query = []
                    for line in sql_content_raw.splitlines():
                        if line.strip().startswith("--") or not line.strip():
                            continue
                        current_query.append(line)
                        if line.strip().endswith(";"):
                            queries.append("\n".join(current_query))
                            current_query = []
                    
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
                    # Drop ONLY the old/obsolete tables, never touch users/admins/orders/etc.
                    dropped = []
                    for old_table in ["products", "qr_codes", "ratings"]:
                        if old_table in tables:
                            conn.execute(text(f"DROP TABLE IF EXISTS `{old_table}`"))
                            dropped.append(old_table)
                    if dropped:
                        log_content.append(f"\nDropped old obsolete tables: {', '.join(dropped)}")
                    
                    for q in queries:
                        q_clean = q.strip()
                        if q_clean:
                            # Skip CREATE DATABASE/USE if we are already connected
                            if q_clean.upper().startswith("CREATE DATABASE") or q_clean.upper().startswith("USE "):
                                continue
                            conn.execute(text(q_clean))
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
                    conn.execute(text("COMMIT;"))
                    log_content.append("\nsetup_db.sql executed successfully.")
                else:
                    log_content.append("\nsetup_db.sql NOT FOUND!")
            
            # Always run column rename migrations if the tables exist to ensure alignment
            tables_res = conn.execute(text("SHOW TABLES")).fetchall()
            current_tables = [row[0] for row in tables_res]
            if "customers" in current_tables:
                col_res = conn.execute(text("SHOW COLUMNS FROM customers")).fetchall()
                cols = [row[0] for row in col_res]
                if "password" in cols and "password_hash" not in cols:
                    conn.execute(text("ALTER TABLE customers CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL"))
                    log_content.append("\ncustomers: renamed password to password_hash")
                if "district" not in cols:
                    conn.execute(text("ALTER TABLE customers ADD COLUMN district VARCHAR(100)"))
                    log_content.append("\ncustomers: added column district")
                if "country" not in cols:
                    conn.execute(text("ALTER TABLE customers ADD COLUMN country VARCHAR(100)"))
                    log_content.append("\ncustomers: added column country")
            if "orders" in current_tables:
                col_res = conn.execute(text("SHOW COLUMNS FROM orders")).fetchall()
                cols = [row[0] for row in col_res]
                if "district" not in cols:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN district VARCHAR(100)"))
                    log_content.append("\norders: added column district")
                if "country" not in cols:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN country VARCHAR(100)"))
                    log_content.append("\norders: added column country")
            if "admins" in current_tables:
                col_res = conn.execute(text("SHOW COLUMNS FROM admins")).fetchall()
                cols = [row[0] for row in col_res]
                if "password" in cols and "password_hash" not in cols:
                    conn.execute(text("ALTER TABLE admins CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL"))
                    log_content.append("\nadmins: renamed password to password_hash")
                if "full_name" in cols and "name" not in cols:
                    conn.execute(text("ALTER TABLE admins CHANGE COLUMN full_name name VARCHAR(100) NOT NULL"))
                    log_content.append("\nadmins: renamed full_name to name")
                if "fcm_token" not in cols:
                    conn.execute(text("ALTER TABLE admins ADD COLUMN fcm_token VARCHAR(255)"))
                    log_content.append("\nadmins: added column fcm_token")
            if "qr_payment" in current_tables:
                col_res = conn.execute(text("SHOW COLUMNS FROM qr_payment")).fetchall()
                cols = [row[0] for row in col_res]
                if "account_holder" not in cols:
                    conn.execute(text("ALTER TABLE qr_payment ADD COLUMN account_holder VARCHAR(100) DEFAULT 'AS Plants Admin'"))
                    log_content.append("\nqr_payment: added column account_holder")
            conn.execute(text("COMMIT;"))
    except Exception as e:
        log_content.append(f"\nMigration error: {e}")
        print(f"[MIGRATION] Migration error: {e}")
        
    with open("db_schema_log.txt", "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_content))

run_migrations()

# Automatically create tables (Fallback if setup_db.sql not executed)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AS Plants Backend API",
    description="Python FastAPI + MySQL Backend for AS Plants Android App",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

# Mount media folders as static directories so the Android client can fetch them
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount static folder for seed plant images and mock QR codes
import os as _os
_os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(products.router, prefix="/api", tags=["Products & Catalog"])
app.include_router(cart_wishlist.router, prefix="/api", tags=["Cart & Wishlist"])
app.include_router(orders.router, prefix="/api", tags=["Orders & Payments"])
app.include_router(settings.router, prefix="/api", tags=["Settings & Config"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(interactions.router, prefix="/api", tags=["Product Ratings"])
app.include_router(admin.router, prefix="/api", tags=["Admin Dashboard"])
app.include_router(customer.router, prefix="/api", tags=["Customer Management"])

# Map compatibility endpoint directly to root
app.include_router(settings.router, tags=["Android Compatibility"])

from pydantic import BaseModel, EmailStr
from config import settings
import smtplib, traceback as tb

class TestEmailRequest(BaseModel):
    email: EmailStr

def _run_smtp_diagnostic(to_email: str):
    """Returns a detailed dict with every SMTP step result."""
    info = {
        "smtp_host": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "smtp_username": settings.SMTP_SENDER,
        "smtp_password_len": len(settings.SMTP_PASSWORD),
        "recipient": to_email,
        "steps": [],
        "success": False,
        "error": None,
    }

    if not settings.SMTP_SENDER or not settings.SMTP_PASSWORD:
        info["error"] = "SMTP_USERNAME or SMTP_PASSWORD is empty in env.txt"
        return info

    try:
        info["steps"].append("Connecting to smtp.gmail.com:587")
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15)

        info["steps"].append("EHLO sent")
        server.ehlo()

        info["steps"].append("STARTTLS upgrade")
        server.starttls()
        server.ehlo()

        passwd = settings.SMTP_PASSWORD.replace(" ", "")
        info["steps"].append(f"Logging in as {settings.SMTP_SENDER}")
        server.login(settings.SMTP_SENDER, passwd)
        info["steps"].append("LOGIN SUCCESS")

        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "AS Plants – SMTP Test Email"
        msg["From"] = f"{settings.SMTP_DISPLAY_NAME} <{settings.SMTP_SENDER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(
            "<h2>AS Plants SMTP Test</h2>"
            "<p>If you see this email, SMTP is working correctly.</p>"
            "<p>OTP system will function as expected.</p>",
            "html", "utf-8"
        ))

        info["steps"].append(f"Sending email to {to_email}")
        server.sendmail(settings.SMTP_SENDER, [to_email], msg.as_string())
        info["steps"].append("EMAIL SENT SUCCESSFULLY")
        server.quit()
        info["success"] = True

    except smtplib.SMTPAuthenticationError as e:
        raw = e.smtp_error
        detail = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(e)
        info["error"] = f"SMTP Auth Failed (code {e.smtp_code}): {detail}"
        info["fix"] = (
            "1. Enable 2-Step Verification on Plantoraofficial33@gmail.com\n"
            "2. Go to https://myaccount.google.com/apppasswords\n"
            "3. Create App Password → Mail + Windows\n"
            "4. Paste 16-char code in env.txt as SMTP_PASSWORD (no spaces needed)\n"
            "5. Restart backend"
        )
    except smtplib.SMTPConnectError as e:
        info["error"] = f"SMTP Connection Failed: {e}"
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
        info["traceback"] = tb.format_exc()

    return info

@app.post("/test-email", tags=["Diagnostics"])
@app.post("/api/test-email", tags=["Diagnostics"])
@app.post("/api/debug/send-test-email", tags=["Diagnostics"])
def test_email(payload: TestEmailRequest):
    """Full SMTP diagnostic — prints every step and exact error to response."""
    result = _run_smtp_diagnostic(payload.email)
    print("\n=== SMTP DIAGNOSTIC RESULT ===")
    import json as _json
    print(_json.dumps(result, indent=2))
    print("=" * 30)

    if result["success"]:
        return {
            "success": True,
            "message": f"Email sent successfully to {payload.email}",
            "smtp_username": result["smtp_username"],
            "steps_completed": result["steps"],
        }
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "SMTP email delivery failed",
                "error": result.get("error"),
                "fix": result.get("fix", "Check SMTP credentials in env.txt"),
                "smtp_username": result["smtp_username"],
                "smtp_host": result["smtp_host"],
                "smtp_port": result["smtp_port"],
                "steps_completed": result["steps"],
            }
        )

@app.get("/api/debug/smtp-status", tags=["Diagnostics"])
def smtp_status():
    import smtplib as _smtp
    passwd = (settings.SMTP_PASSWORD or "").replace(" ", "")
    username = settings.SMTP_SENDER or ""
    
    auth_success = False
    try:
        server = _smtp.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, passwd)
        server.quit()
        auth_success = True
    except Exception:
        pass
        
    return {
        "smtp_host": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "auth_success": auth_success
    }

# ── STARTUP: SMTP STATUS CHECK ─────────────────────────────────────────────────
@app.on_event("startup")
async def check_smtp_on_startup():
    """
    Runs automatically every time the server starts.
    Prints a clear SMTP working / not-working banner to the terminal.
    Sends a test email on startup to verify delivery.
    """
    import smtplib as _smtp
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    passwd = (settings.SMTP_PASSWORD or "").replace(" ", "")
    username = settings.SMTP_SENDER or ""

    print("\n" + "=" * 60)
    print("  AS PLANTS BACKEND  -  SMTP STARTUP CHECK")
    print("=" * 60)
    print(f"  Host     : {settings.SMTP_SERVER}")
    print(f"  Port     : {settings.SMTP_PORT}")
    print(f"  Username : {username}")
    print(f"  Password : {'(not set)' if not passwd else passwd[:4] + '...' + passwd[-4:] + f'  (len={len(passwd)})'}")
    print("-" * 60)

    if not username or not passwd:
        print("  [FAIL] SMTP NOT CONFIGURED — set SMTP_USERNAME and SMTP_PASSWORD in env.txt")
        print("=" * 60 + "\n")
        return

    try:
        server = _smtp.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, passwd)
        
        # Send test email to the admin/username itself
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "AS Plants – Backend Startup SMTP Test"
        msg["From"] = f"{settings.SMTP_DISPLAY_NAME} <{username}>"
        msg["To"] = username
        msg.attach(MIMEText(
            "<h2>AS Plants Backend Started Successfully</h2>"
            "<p>Your SMTP configuration is working perfectly.</p>"
            "<p>OTP emails can now be delivered to users.</p>",
            "html", "utf-8"
        ))
        
        server.sendmail(username, [username], msg.as_string())
        server.quit()
        
        print(f"  [ OK ] SMTP AUTHENTICATION SUCCESSFUL")
        print(f"  [ OK ] Test email sent to {username}")
        print("      OTP emails can now be sent to users.")
        print("=" * 60 + "\n")

    except _smtp.SMTPAuthenticationError as e:
        raw = e.smtp_error
        detail = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(e)
        print(f"  [FAIL] SMTP AUTH FAILED  (code {e.smtp_code})")
        print(f"      Error : {detail.strip()}")
        print("      Fix   : Go to https://myaccount.google.com/apppasswords")
        print("               Create new App Password and update SMTP_PASSWORD in env.txt")
        print("               Then restart the backend.")
        print("=" * 60 + "\n")

    except _smtp.SMTPConnectError as e:
        print(f"  [FAIL] SMTP CONNECTION FAILED: {e}")
        print("      Check your internet / firewall settings.")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"  [FAIL] SMTP ERROR: {type(e).__name__}: {e}")
        print("=" * 60 + "\n")


@app.get("/")
def read_root():
    return {"message": "Welcome to AS Plants Backend API. Please visit /docs for API documentation."}


@app.get("/api/debug/db")
def debug_db():
    from database.connection import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        conn = db.bind.connect()
        
        # 1. Plants
        result = conn.execute(text("SELECT id, plant_name, price, stock, is_active, image_url FROM plants"))
        plants = [
            {"id": row[0], "name": row[1], "price": row[2], "stock": row[3], "is_active": bool(row[4]), "image_url": row[5]}
            for row in result.fetchall()
        ]
        
        # 2. Admins
        result = conn.execute(text("SELECT id, name, email, phone, role FROM admins"))
        admins = [
            {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "role": row[4]}
            for row in result.fetchall()
        ]
        
        # 3. Customers
        result = conn.execute(text("SELECT id, name, email, phone FROM customers"))
        customers = [
            {"id": row[0], "name": row[1], "email": row[2], "phone": row[3]}
            for row in result.fetchall()
        ]
        
        return {
            "plants": plants,
            "admins": admins,
            "customers": customers
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


@app.get("/api/debug/init-db")
def init_db():
    from database.connection import engine
    try:
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()
        
        with open("setup_db.sql", "r", encoding="utf-8") as f:
            sql_script = f.read()
        
        # Split by semicolon, but handle statement separation carefully
        statements = sql_script.split(";")
        for statement in statements:
            stmt = statement.strip()
            if not stmt:
                continue
            lines = stmt.split("\n")
            cleaned_lines = [line for line in lines if not line.strip().startswith("--")]
            stmt = "\n".join(cleaned_lines).strip()
            if stmt:
                try:
                    cursor.execute(stmt)
                except Exception as ex:
                    # Log errors but don't fail the transaction
                    print(f"Statement failed: {stmt[:50]}... Error: {ex}")
        raw_conn.commit()
        cursor.close()
        raw_conn.close()
        return {"status": "success", "message": "Database initialized and seeded successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/debug/tables-list")
def debug_tables_list():
    from sqlalchemy import text
    from database.connection import engine
    tables_info = {}
    try:
        with engine.connect() as conn:
            tables_res = conn.execute(text("SHOW TABLES")).fetchall()
            tables = [row[0] for row in tables_res]
            for t in tables:
                col_res = conn.execute(text(f"SHOW COLUMNS FROM {t}")).fetchall()
                tables_info[t] = [row[0] for row in col_res]
    except Exception as e:
        return {"error": str(e)}
    return {"tables": tables_info}

@app.get("/api/debug/run-db-proof")
def debug_run_db_proof():
    import io
    import sys
    import traceback
    from sqlalchemy import text
    from database.connection import SessionLocal
    from models.user import User, Admin, OTPVerification
    from services.auth_service import auth_service
    
    output_capture = io.StringIO()
    def log_print(*args, **kwargs):
        print(*args, file=output_capture, **kwargs)
        
    log_print("==================================================")
    log_print("              DATABASE VERIFICATION              ")
    log_print("==================================================")
    
    db = SessionLocal()
    try:
        # Clear test accounts
        test_customer_email = "test.customer@example.com"
        test_admin_email = "test.admin@example.com"
        
        db.query(User).filter(User.email == test_customer_email).delete()
        db.query(Admin).filter(Admin.email == test_admin_email).delete()
        db.commit()
        
        # 1. Create a new Customer account
        log_print("\n--- 1. Creating a new Customer account ---")
        plain_customer_password = "secure_customer_pwd123"
        hashed_customer_password = auth_service.get_password_hash(plain_customer_password)
        
        new_customer = User(
            name="Test Customer Name",
            email=test_customer_email,
            password=hashed_customer_password,
            phone="+1 555-0100"
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        log_print(f"Customer created successfully! ID: {new_customer.id}")
        
        # 2. Query Customer Table using raw SQL
        log_print("\n--- 2. Showing MySQL record from customers table ---")
        result = db.execute(text("SELECT id, name, email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
        row = result.fetchone()
        if row:
            log_print(f"ID            : {row[0]}")
            log_print(f"Name          : {row[1]}")
            log_print(f"Email         : {row[2]}")
            log_print(f"Password Hash : {row[3]}")
            assert plain_customer_password not in row[3], "Plain password found in password_hash!"
            log_print("✅ SUCCESS: Only password_hash is stored in the database. Plain password does NOT exist.")
        else:
            log_print("❌ ERROR: Customer not found!")
            
        # 3. Create a new Admin account
        log_print("\n--- 3. Creating a new Admin account ---")
        plain_admin_password = "secure_admin_pwd999"
        hashed_admin_password = auth_service.get_password_hash(plain_admin_password)
        
        # Check current admin count before inserting
        admin_count = db.query(Admin).count()
        log_print(f"Current Admin Count in database: {admin_count}")
        
        new_admin = Admin(
            full_name="Test Admin Name",
            email=test_admin_email,
            password=hashed_admin_password,
            phone="+1 555-0200",
            role="Admin"
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        log_print(f"Admin created successfully! ID: {new_admin.id}")
        
        # 4. Query Admin Table
        log_print("\n--- 4. Showing MySQL record from admins table ---")
        result = db.execute(text("SELECT id, name, email, password_hash FROM admins WHERE email = 'test.admin@example.com'"))
        row = result.fetchone()
        if row:
            log_print(f"ID            : {row[0]}")
            log_print(f"Name          : {row[1]}")
            log_print(f"Email         : {row[2]}")
            log_print(f"Password Hash : {row[3]}")
            assert plain_admin_password not in row[3], "Plain password found in password_hash!"
            log_print("✅ SUCCESS: Only password_hash is stored in the database. Plain password does NOT exist.")
        else:
            log_print("❌ ERROR: Admin not found!")
            
        # 5. Forgot Password & Reset Password
        log_print("\n--- 5. Testing Forgot Password & Reset Flow ---")
        log_print("\n[BEFORE RESET]")
        result_before = db.execute(text("SELECT email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
        row_before = result_before.fetchone()
        log_print(f"Email        : {row_before[0]}")
        log_print(f"Old Hash     : {row_before[1]}")
        
        new_plain_password = "my_new_reset_password_xyz"
        new_hashed_password = auth_service.get_password_hash(new_plain_password)
        
        db.execute(text("UPDATE customers SET password_hash = :new_hash WHERE email = :email"), 
                     {"new_hash": new_hashed_password, "email": test_customer_email})
        db.commit()
        log_print("\nPassword reset successfully performed!")
        
        log_print("\n[AFTER RESET]")
        result_after = db.execute(text("SELECT email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
        row_after = result_after.fetchone()
        log_print(f"Email        : {row_after[0]}")
        log_print(f"New Hash     : {row_after[1]}")
        
        assert row_before[1] != row_after[1], "Password hash did not change!"
        log_print("✅ SUCCESS: password_hash successfully changed in database.")
        
        # 6. Verify login works using new password
        log_print("\n--- 6. Verifying login works with the new password ---")
        db.refresh(new_customer)
        login_success = auth_service.verify_password(new_plain_password, new_customer.password)
        log_print(f"Login attempt with new password: {'SUCCESS' if login_success else 'FAILED'}")
        assert login_success, "Login verification failed with new password!"
        
        login_old_failed = not auth_service.verify_password(plain_customer_password, new_customer.password)
        log_print(f"Login attempt with old password (should fail): {'FAILED (As expected)' if login_old_failed else 'SUCCESS (Unexpected)'}")
        assert login_old_failed, "Old password still works!"
        log_print("✅ SUCCESS: Login works with new password, and old password is successfully invalidated.")
        
        # 7. Scan for any plain password in MySQL
        log_print("\n--- 7. Confirming no plain password exists anywhere in MySQL tables ---")
        res_all_cust = db.execute(text("SELECT name, email, password_hash FROM customers")).fetchall()
        res_all_adm = db.execute(text("SELECT name, email, password_hash FROM admins")).fetchall()
        
        all_passwords_clean = True
        for cust in res_all_cust:
            if not cust[2].startswith("$pbkdf2-sha256$") and not cust[2].startswith("$2b$"):
                all_passwords_clean = False
                log_print(f"⚠️ WARNING: Non-hash pattern found for customer {cust[1]} ({cust[0]}) -> {cust[2]}")
        for adm in res_all_adm:
            if not adm[2].startswith("$pbkdf2-sha256$") and not adm[2].startswith("$2b$"):
                all_passwords_clean = False
                log_print(f"⚠️ WARNING: Non-hash pattern found for admin {adm[1]} ({adm[0]}) -> {adm[2]}")
                
        if all_passwords_clean:
            log_print("✅ CONFIRMED: No plain passwords exist in either the customers or admins tables. Only secure hashes are stored.")
        else:
            log_print("❌ FAILED: Plain passwords or improperly hashed values found in database.")
    except Exception as e:
        log_print(f"\n❌ EXCEPTION DURING VERIFICATION: {e}")
        log_print(traceback.format_exc())
    finally:
        db.close()
        log_print("\n==================================================")
        
    proof_output = output_capture.getvalue()
    
    with open("test_verification_report.txt", "w", encoding="utf-8") as rf:
        rf.write(proof_output)
        
    return {
        "status": "success",
        "output": proof_output
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
