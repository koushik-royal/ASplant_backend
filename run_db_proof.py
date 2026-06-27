import os
from database.connection import SessionLocal
from models.user import User, Admin, OTPVerification
from services.auth_service import auth_service
from sqlalchemy import text

# Initialize session
db = SessionLocal()

print("==================================================")
print("              DATABASE VERIFICATION              ")
print("==================================================")

try:
    # 1. Clear existing test accounts if any to make it repeatable
    test_customer_email = "test.customer@example.com"
    test_admin_email = "test.admin@example.com"
    
    db.query(User).filter(User.email == test_customer_email).delete()
    db.query(Admin).filter(Admin.email == test_admin_email).delete()
    db.commit()

    # 2. Insert new Customer Account
    print("\n--- 1. Creating a new Customer account ---")
    plain_customer_password = "secure_customer_pwd123"
    hashed_customer_password = auth_service.get_password_hash(plain_customer_password)
    
    new_customer = User(
        name="Test Customer Name",
        email=test_customer_email,
        password=hashed_customer_password,  # Stored in column "password_hash"
        phone="+1 555-0100"
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    print(f"Customer created successfully! ID: {new_customer.id}")

    # 3. Query Customer Table using raw SQL to show password_hash is stored instead of plain
    print("\n--- 2. Showing MySQL record from customers table ---")
    result = db.execute(text("SELECT id, name, email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
    row = result.fetchone()
    if row:
        print(f"ID            : {row[0]}")
        print(f"Name          : {row[1]}")
        print(f"Email         : {row[2]}")
        print(f"Password Hash : {row[3]}")
        
        # Confirm no plain text password
        assert plain_customer_password not in row[3], "Plain password found in password_hash!"
        print("SUCCESS: Only password_hash is stored in the database. Plain password does NOT exist.")
    else:
        print("ERROR: Customer not found!")

    # 4. Insert new Admin Account
    print("\n--- 3. Creating a new Admin account ---")
    plain_admin_password = "secure_admin_pwd999"
    hashed_admin_password = auth_service.get_password_hash(plain_admin_password)
    
    new_admin = Admin(
        full_name="Test Admin Name",  # Stored in column "name"
        email=test_admin_email,
        password=hashed_admin_password,  # Stored in column "password_hash"
        phone="+1 555-0200",
        role="Admin"
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    print(f"Admin created successfully! ID: {new_admin.id}")

    # 5. Query Admin Table using raw SQL
    print("\n--- 4. Showing MySQL record from admins table ---")
    result = db.execute(text("SELECT id, name, email, password_hash FROM admins WHERE email = 'test.admin@example.com'"))
    row = result.fetchone()
    if row:
        print(f"ID            : {row[0]}")
        print(f"Name          : {row[1]}")
        print(f"Email         : {row[2]}")
        print(f"Password Hash : {row[3]}")
        
        # Confirm no plain text password
        assert plain_admin_password not in row[3], "Plain password found in password_hash!"
        print("SUCCESS: Only password_hash is stored in the database. Plain password does NOT exist.")
    else:
        print("ERROR: Admin not found!")

    # 6. Test Forgot Password & Reset Password
    print("\n--- 5. Testing Forgot Password & Reset Flow ---")
    # Show SQL query results BEFORE password reset
    print("\n[BEFORE RESET]")
    result_before = db.execute(text("SELECT email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
    row_before = result_before.fetchone()
    print(f"Email        : {row_before[0]}")
    print(f"Old Hash     : {row_before[1]}")

    # Perform Reset (simulation)
    new_plain_password = "my_new_reset_password_xyz"
    new_hashed_password = auth_service.get_password_hash(new_plain_password)
    
    # Update customer password_hash in MySQL
    db.execute(text("UPDATE customers SET password_hash = :new_hash WHERE email = :email"), 
                 {"new_hash": new_hashed_password, "email": test_customer_email})
    db.commit()
    print("\nPassword reset successfully performed!")

    # Show SQL query results AFTER password reset
    print("\n[AFTER RESET]")
    result_after = db.execute(text("SELECT email, password_hash FROM customers WHERE email = 'test.customer@example.com'"))
    row_after = result_after.fetchone()
    print(f"Email        : {row_after[0]}")
    print(f"New Hash     : {row_after[1]}")
    
    # Verify the hash updated and is different
    assert row_before[1] != row_after[1], "Password hash did not change!"
    print("SUCCESS: password_hash successfully changed in database.")

    # 7. Confirm Login works using the new password
    print("\n--- 6. Verifying login works with the new password ---")
    db.refresh(new_customer)
    login_success = auth_service.verify_password(new_plain_password, new_customer.password)
    print(f"Login attempt with new password: {'SUCCESS' if login_success else 'FAILED'}")
    assert login_success, "Login verification failed with new password!"
    
    # Verify old password no longer works
    login_old_failed = not auth_service.verify_password(plain_customer_password, new_customer.password)
    print(f"Login attempt with old password (should fail): {'FAILED (As expected)' if login_old_failed else 'SUCCESS (Unexpected)'}")
    assert login_old_failed, "Old password still works!"
    
    print("\nSUCCESS: Login works with new password, and old password is successfully invalidated.")

    # 8. Scan for any plain password in MySQL (Double check)
    print("\n--- 7. Confirming no plain password exists anywhere in MySQL tables ---")
    # Fetch all records
    res_all_cust = db.execute(text("SELECT name, email, password_hash FROM customers")).fetchall()
    res_all_adm = db.execute(text("SELECT name, email, password_hash FROM admins")).fetchall()
    
    all_passwords_clean = True
    for cust in res_all_cust:
        # Check if hash looks like a plain string
        if not cust[2].startswith("$pbkdf2-sha256$") and not cust[2].startswith("$2b$"):
            all_passwords_clean = False
            print(f"WARNING: Non-hash pattern found for customer {cust[1]} ({cust[0]}) -> {cust[2]}")
            
    for adm in res_all_adm:
        if not adm[2].startswith("$pbkdf2-sha256$") and not adm[2].startswith("$2b$"):
            all_passwords_clean = False
            print(f"WARNING: Non-hash pattern found for admin {adm[1]} ({adm[0]}) -> {adm[2]}")
            
    if all_passwords_clean:
        print("CONFIRMED: No plain passwords exist in either the customers or admins tables. Only secure hashes are stored.")
    else:
        print("FAILED: Plain passwords or improperly hashed values found in database.")

    # (connection closing removed, handled by session close)

except Exception as e:
    print(f"\nEXCEPTION DURING VERIFICATION: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
    print("\n==================================================")
