import requests
import os
import sys
from sqlalchemy import text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.connection import SessionLocal
# Import all models to register in class registry
import models.interaction
import models.order
import models.setting
from models.product import Product
from models.user import Admin, User
from services.auth_service import auth_service

BASE_URL = "http://localhost:8000/api"

def print_banner(title):
    print("\n" + "=" * 60)
    print(f" {title.upper():^58}")
    print("=" * 60)

def test_logins():
    print_banner("1. Login Verification")
    
    # Existing Admin credentials
    admin_payload = {"email": "admin@plantora.com", "password": "adminpassword"}
    print(f"Testing Admin Login for: {admin_payload['email']}...")
    res = requests.post(f"{BASE_URL}/admin/login", json=admin_payload)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 200, "Admin login failed!"
    assert res.json()["status"] == "success", "Admin login status not success!"
    print("SUCCESS: Admin Login successful (200 OK)")

    # Existing Customer credentials
    cust_payload = {"email": "alex.mercer@plantora.com", "password": "customerpassword"}
    print(f"\nTesting Customer Login for: {cust_payload['email']}...")
    res = requests.post(f"{BASE_URL}/auth/login", json=cust_payload)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 200, "Customer login failed!"
    assert res.json()["status"] == "success", "Customer login status not success!"
    print("SUCCESS: Customer Login successful (200 OK)")

def test_admin_profile_update():
    print_banner("2. Admin Profile Update")
    
    # 1. Fetch current profile
    email = "admin@plantora.com"
    print(f"Fetching current profile for: {email}...")
    res = requests.get(f"{BASE_URL}/admin/profile/{email}")
    print(f"Current Admin: {res.json()['admin']}")
    original_admin = res.json()['admin']
    
    # 2. Update name, phone, and role
    update_payload = {
        "full_name": "Super Admin E2E",
        "phone": "+91 99999 88888",
        "role": "Super Admin"
    }
    print(f"\nUpdating Admin profile...")
    res = requests.put(f"{BASE_URL}/admin/profile/{email}", json=update_payload)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 200, "Admin profile update failed!"
    
    # Verify in DB
    db = SessionLocal()
    try:
        admin_in_db = db.query(Admin).filter(Admin.email == email).first()
        print(f"\nVerifying in MySQL Database:")
        print(f"Name in DB  : {admin_in_db.full_name} (Expected: {update_payload['full_name']})")
        print(f"Phone in DB : {admin_in_db.phone} (Expected: {update_payload['phone']})")
        print(f"Role in DB  : {admin_in_db.role} (Expected: {update_payload['role']})")
        print(f"Email in DB : {admin_in_db.email} (Expected: {email} - Read-Only Check)")
        
        assert admin_in_db.full_name == update_payload["full_name"], "Name not updated in DB!"
        assert admin_in_db.phone == update_payload["phone"], "Phone not updated in DB!"
        assert admin_in_db.role == update_payload["role"], "Role not updated in DB!"
        assert admin_in_db.email == email, "Email changed unexpectedly!"
        print("SUCCESS: Admin Profile updated and verified in database successfully.")
        
        # Restore original admin profile
        admin_in_db.full_name = original_admin["full_name"]
        admin_in_db.phone = original_admin["phone"]
        admin_in_db.role = original_admin["role"]
        db.commit()
        print("SUCCESS: Original Admin Profile restored.")
    finally:
        db.close()

def test_add_plant_with_image():
    print_banner("3. Admin Adds Plant with Image")
    
    # 1. Create a plant
    plant_payload = {
        "name": "E2E Golden Pothos",
        "category": "Indoor",
        "price": 299,
        "description": "Dynamic E2E Verification Plant.",
        "stock_quantity": 30
    }
    print(f"Creating plant: {plant_payload['name']}...")
    res = requests.post(f"{BASE_URL}/products", json=plant_payload)
    print(f"Create Product Status Code: {res.status_code}")
    product = res.json()
    print(f"Created Product: {product}")
    product_id = product["id"]
    
    # 2. Upload test image
    print(f"\nUploading image for product ID: {product_id}...")
    # Create a small dummy image in tests/
    dummy_img_path = os.path.join(os.path.dirname(__file__), "dummy_plant.jpg")
    with open(dummy_img_path, "wb") as f:
        # Write minimal JPEG header/bytes
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\x00\xff\xd9")
    
    with open(dummy_img_path, "rb") as f:
        files = [("files", ("dummy_plant.jpg", f, "image/jpeg"))]
        res = requests.post(f"{BASE_URL}/products/{product_id}/images", files=files)
        
    print(f"Upload Image Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 200, "Image upload failed!"
    uploaded_url = res.json()["images"][0]
    print(f"Uploaded Image URL: {uploaded_url}")
    
    # 3. Verify MySQL storage
    db = SessionLocal()
    try:
        plant_in_db = db.query(Product).filter(Product.id == product_id).first()
        print(f"\nVerifying stored details in MySQL:")
        print(f"Plant ID    : {plant_in_db.id}")
        print(f"Plant Name  : {plant_in_db.name}")
        print(f"Price       : {plant_in_db.price}")
        print(f"Stock       : {plant_in_db.stock_quantity}")
        print(f"Image URL   : {plant_in_db.image_url}")
        
        assert plant_in_db.image_url == uploaded_url, "Stored image URL doesn't match uploaded path!"
        print("SUCCESS: MySQL verification successful: Plant and exact uploaded image URL stored successfully.")
        
        # 4. Customer Visibility (Instant appearance check)
        print("\nChecking Customer visibility endpoint `/products`...")
        res_cust = requests.get(f"{BASE_URL}/products")
        all_plants = res_cust.json()
        found_in_catalog = False
        for p in all_plants:
            if p["id"] == product_id:
                found_in_catalog = True
                print(f"Instant Customer Visibility check: Found plant in catalog!")
                print(f"Name  : {p['name']}")
                print(f"Price : {p['price']}")
                print(f"Image : {p['image_url']}")
                assert p["image_url"] == uploaded_url, "Customer-facing image URL mismatch!"
                
        assert found_in_catalog, "Created plant did NOT immediately appear in customer catalog!"
        print("SUCCESS: Customer Visibility successful: Plant immediately appeared in Customer Home / catalog.")
        
        # Clean up the test plant
        db.delete(plant_in_db)
        db.commit()
        print("\nSUCCESS: Cleaned up E2E verification test plant from database.")
    finally:
        db.close()
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)

def test_product_delete_api():
    print_banner("4. Product Soft-Delete API Verification")
    
    # 1. Create a plant
    plant_payload = {
        "name": "Delete Test Plant",
        "category": "Outdoor",
        "price": 150,
        "description": "Delete Test Plant Description.",
        "stock_quantity": 5
    }
    print(f"Creating test plant: {plant_payload['name']}...")
    res = requests.post(f"{BASE_URL}/products", json=plant_payload)
    assert res.status_code == 200, "Create product failed!"
    product = res.json()
    product_id = product["id"]
    print(f"Created Product ID: {product_id}")
    
    # 2. Upload image to create physical file
    dummy_img_path = os.path.join(os.path.dirname(__file__), "delete_dummy_plant.jpg")
    with open(dummy_img_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\x00\xff\xd9")
    
    with open(dummy_img_path, "rb") as f:
        files = [("files", ("delete_dummy_plant.jpg", f, "image/jpeg"))]
        res = requests.post(f"{BASE_URL}/products/{product_id}/images", files=files)
    assert res.status_code == 200, "Upload image failed!"
    uploaded_url = res.json()["images"][0]
    print(f"Uploaded Image URL: {uploaded_url}")
    
    # Verify file exists on disk before delete
    filename = uploaded_url.split("uploads/products/")[-1]
    local_image_path = os.path.join("uploads", "products", filename)
    print(f"Checking physical image path: {local_image_path}")
    assert os.path.exists(local_image_path), f"Physical image file {local_image_path} does not exist before delete!"
    print("SUCCESS: Physical image file exists before soft-deletion.")
    
    # 3. Call Delete Product API (soft delete)
    print(f"\nSoft-deleting product {product_id} via API...")
    res = requests.delete(f"{BASE_URL}/products/{product_id}")
    print(f"Delete API Status Code: {res.status_code}")
    print(f"Delete API Response: {res.json()}")
    assert res.status_code == 200, "Delete API failed!"
    assert res.json()["status"] == "success", "Delete status not success!"
    
    # 4. Verify product STILL EXISTS in database (soft delete — record preserved)
    print("\nVerifying product still exists in database with status='deleted'...")
    db = SessionLocal()
    try:
        plant_in_db = db.query(Product).filter(Product.id == product_id).first()
        assert plant_in_db is not None, "Product was hard-deleted from database! Expected soft-delete."
        assert plant_in_db.status == "deleted", f"Expected status='deleted' but got '{plant_in_db.status}'"
        assert plant_in_db.is_active == False, "Expected is_active=False after soft-delete"
        print(f"SUCCESS: Product still in DB with status='{plant_in_db.status}', is_active={plant_in_db.is_active}")
    finally:
        db.close()
        
    # 5. Verify physical image file is PRESERVED on disk (soft delete keeps images)
    print(f"\nVerifying physical image file {local_image_path} still exists on disk...")
    assert os.path.exists(local_image_path), "Physical image file was deleted! Expected it to remain after soft-delete."
    print("SUCCESS: Physical image file preserved on disk (soft-delete keeps images).")

    # 6. Verify product is hidden from the public product listing
    print("\nVerifying product is hidden from public listings...")
    res_list = requests.get(f"{BASE_URL}/products")
    assert res_list.status_code == 200, "Product listing endpoint failed!"
    ids_in_listing = [p["id"] for p in res_list.json()]
    assert product_id not in ids_in_listing, "Soft-deleted product still visible in public listings!"
    print("SUCCESS: Soft-deleted product correctly hidden from public product listing.")
    
    # 7. Clean up: Hard-delete the test product directly from DB
    db = SessionLocal()
    try:
        plant_in_db = db.query(Product).filter(Product.id == product_id).first()
        if plant_in_db:
            db.delete(plant_in_db)
            db.commit()
        print("\nSUCCESS: Cleaned up soft-deleted test plant from database.")
    finally:
        db.close()
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)
        if os.path.exists(local_image_path):
            os.remove(local_image_path)


def test_soft_delete_visibility_with_purchase():
    print_banner("5. Soft-Delete: Visibility for Past Purchasers")

    # 1. Create a test plant
    plant_payload = {
        "name": "Soft Delete Visibility Plant",
        "category": "Indoor",
        "price": 499,
        "description": "Plant used for soft-delete visibility test.",
        "stock_quantity": 10
    }
    res = requests.post(f"{BASE_URL}/products", json=plant_payload)
    assert res.status_code == 200, "Create product failed!"
    product_id = res.json()["id"]
    print(f"Created Product ID: {product_id}")

    # 2. Create a test customer
    db = SessionLocal()
    try:
        test_customer = User(
            email="softdelete.test@plantora.com",
            password=auth_service.get_password_hash("testpassword"),
            name="Soft Delete Tester",
            phone="+91 99988 77766",
        )
        db.add(test_customer)
        db.flush()
        customer_id = test_customer.id
        print(f"Created test customer ID: {customer_id}")

        # 3. Create a fake order referencing the product
        from models.order import Order, OrderItem
        import datetime
        fake_order = Order(
            order_id=f"PLT_SDT_{product_id}",
            user_id=customer_id,
            date="20 Jun 2026",
            status="Delivered",
            subtotal=499,
            delivery_charge=0,
            total_amount=499,
            full_name="Soft Delete Tester",
            phone_number="+91 99988 77766",
            pincode="560001",
            address_line="Test Address",
            city="Bangalore",
            state="Karnataka",
            payment_method="COD"
        )
        db.add(fake_order)
        db.flush()

        fake_item = OrderItem(
            order_id=fake_order.order_id,
            product_id=product_id,
            quantity=1,
            price=499
        )
        db.add(fake_item)
        db.commit()
        print("Created fake order and order item.")
    finally:
        db.close()

    # 4. Soft-delete the product
    res = requests.delete(f"{BASE_URL}/products/{product_id}")
    assert res.status_code == 200, "Soft-delete API failed!"
    print("Product soft-deleted via API.")

    # 5. Verify product NOT visible in public listing
    res_list = requests.get(f"{BASE_URL}/products")
    ids_in_listing = [p["id"] for p in res_list.json()]
    assert product_id not in ids_in_listing, "Soft-deleted product visible in public listing!"
    print("SUCCESS: Product hidden from public listing.")

    # 6. Verify product NOT accessible by unauthenticated (no email) request
    res_anon = requests.get(f"{BASE_URL}/products/{product_id}")
    assert res_anon.status_code == 404, f"Expected 404 for anonymous request, got {res_anon.status_code}"
    print("SUCCESS: Product returns 404 for anonymous/non-purchaser requests.")

    # 7. Verify product IS accessible by the past purchaser (with email)
    res_buyer = requests.get(f"{BASE_URL}/products/{product_id}", params={"email": "softdelete.test@plantora.com"})
    assert res_buyer.status_code == 200, f"Expected 200 for purchaser request, got {res_buyer.status_code}"
    assert res_buyer.json()["status"] == "deleted", "Expected status='deleted' in response"
    print("SUCCESS: Product accessible by past purchaser with 'deleted' status.")

    # 8. Verify add-to-cart is blocked for soft-deleted product
    res_cart = requests.post(
        f"{BASE_URL}/cart/add",
        params={"email": "softdelete.test@plantora.com"},
        json={"product_id": product_id, "quantity": 1}
    )
    assert res_cart.status_code == 400, f"Expected 400 for cart add of deleted product, got {res_cart.status_code}"
    print("SUCCESS: Add-to-cart blocked for soft-deleted product (400).")

    # 9. Verify wishlist-toggle is blocked for soft-deleted product
    res_wish = requests.post(
        f"{BASE_URL}/wishlist/toggle",
        params={"email": "softdelete.test@plantora.com"},
        json={"product_id": product_id}
    )
    assert res_wish.status_code == 400, f"Expected 400 for wishlist add of deleted product, got {res_wish.status_code}"
    print("SUCCESS: Wishlist add blocked for soft-deleted product (400).")

    # 10. Cleanup: remove test order, items, customer, and product from DB
    db = SessionLocal()
    try:
        from models.order import OrderItem, Order
        db.query(OrderItem).filter(OrderItem.order_id == f"PLT_SDT_{product_id}").delete(synchronize_session=False)
        db.query(Order).filter(Order.order_id == f"PLT_SDT_{product_id}").delete(synchronize_session=False)
        db.query(User).filter(User.email == "softdelete.test@plantora.com").delete(synchronize_session=False)
        plant_in_db = db.query(Product).filter(Product.id == product_id).first()
        if plant_in_db:
            db.delete(plant_in_db)
        db.commit()
        print("Cleanup: Test data removed from database.")
    finally:
        db.close()


if __name__ == "__main__":
    print_banner("AS Plants Backend E2E Validation")

    # 1. Setup: Seed test customer alex.mercer@plantora.com if not present
    db = SessionLocal()
    try:
        alex = db.query(User).filter(User.email == "alex.mercer@plantora.com").first()
        if not alex:
            alex = User(
                email="alex.mercer@plantora.com",
                password=auth_service.get_password_hash("customerpassword"),
                name="Alex Mercer",
                phone="+91 98765 43210",
                gender="Male",
                dob="12 Aug 1995",
                address="123, Green Park Layout, Near Central Mall",
                city="Bangalore",
                state="Karnataka",
                pincode="560001"
            )
            db.add(alex)
            db.commit()
            print("Setup: Seeded test customer alex.mercer@plantora.com")
        else:
            print("Setup: alex.mercer@plantora.com already exists.")
    except Exception as e:
        print(f"Error seeding test user: {e}")
    finally:
        db.close()

    try:
        # 2. Run verification tests
        test_logins()
        test_admin_profile_update()
        test_add_plant_with_image()
        test_product_delete_api()
        test_soft_delete_visibility_with_purchase()
    finally:
        # 3. Teardown: Remove alex.mercer test customer
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == "alex.mercer@plantora.com").delete()
            db.commit()
            print("Teardown: Removed test customer alex.mercer@plantora.com")
        except Exception as e:
            print(f"Error cleaning up test user: {e}")
        finally:
            db.close()

    print_banner("E2E Validation Complete: ALL TESTS PASSED")
