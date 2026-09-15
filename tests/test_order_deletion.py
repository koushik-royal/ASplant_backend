import os
import sys
import unittest
from fastapi import HTTPException

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database.connection import SessionLocal, engine
from models.order import Order, OrderItem, DeliveryTracking, DeliveryProof, Payment
from models.interaction import Notification, Rating
from models.user import Admin, User
from models.product import Product
from routers.orders import delete_order

class TestOrderDeletionEndpoint(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Ensure a test admin exists
        self.test_admin_email = "test_admin@plantora.com"
        admin = self.db.query(Admin).filter(Admin.email == self.test_admin_email).first()
        if not admin:
            admin = Admin(
                email=self.test_admin_email,
                password="hashed_test_password",
                full_name="Test Admin",
                role="Admin"
            )
            self.db.add(admin)
            self.db.commit()

        # Ensure a test customer exists
        self.test_customer_email = "test_customer@plantora.com"
        user = self.db.query(User).filter(User.email == self.test_customer_email).first()
        if not user:
            user = User(
                email=self.test_customer_email,
                password="hashed_test_password",
                name="Test Customer"
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        self.user_id = user.id

    def tearDown(self):
        # Clean up test admin and customer
        self.db.query(Admin).filter(Admin.email == self.test_admin_email).delete()
        self.db.query(User).filter(User.email == self.test_customer_email).delete()
        self.db.commit()
        self.db.close()

    def test_route_registration(self):
        """Verify DELETE /api/orders/{order_id} is registered in FastAPI app."""
        routes = [
            (route.path, list(route.methods))
            for route in app.routes
            if hasattr(route, "methods")
        ]
        has_delete_order = any(
            path == "/api/orders/{order_id}" and "DELETE" in methods
            for path, methods in routes
        )
        self.assertTrue(has_delete_order, "Route DELETE /api/orders/{order_id} is not registered in FastAPI app")
        print(" [PASS] Route DELETE /api/orders/{order_id} correctly registered.")

    def test_unauthorized_no_email(self):
        """Verify 401 when no admin email is provided."""
        with self.assertRaises(HTTPException) as cm:
            delete_order(
                order_id="#PLT_NONEXISTENT",
                admin_email=None,
                x_admin_email=None,
                db=self.db
            )
        self.assertEqual(cm.exception.status_code, 401)
        print(" [PASS] 401 Unauthorized raised when no admin email provided.")

    def test_forbidden_non_admin_email(self):
        """Verify 403 when email does not belong to an Admin."""
        with self.assertRaises(HTTPException) as cm:
            delete_order(
                order_id="#PLT_NONEXISTENT",
                admin_email=self.test_customer_email,
                x_admin_email=None,
                db=self.db
            )
        self.assertEqual(cm.exception.status_code, 403)
        print(" [PASS] 403 Forbidden raised when non-admin email provided.")

    def test_not_found_order(self):
        """Verify 404 when order does not exist."""
        with self.assertRaises(HTTPException) as cm:
            delete_order(
                order_id="#PLT_DOESNOTEXIST_99999",
                admin_email=self.test_admin_email,
                x_admin_email=None,
                db=self.db
            )
        self.assertEqual(cm.exception.status_code, 404)
        print(" [PASS] 404 Not Found raised for non-existent order.")

    def test_safe_full_cascade_order_deletion(self):
        """Verify full deletion of order, items, tracking, payment, proof, rating, and notifications."""
        test_order_id = "#PLT_TEST_DELETE_101"

        # 1. Create dummy order
        order = Order(
            order_id=test_order_id,
            user_id=self.user_id,
            date="16 Sep 2026, 03:00 AM",
            status="Cancelled",
            subtotal=100,
            delivery_charge=0,
            total_amount=100,
            full_name="Test Customer",
            phone_number="1234567890",
            pincode="123456",
            address_line="Test Address",
            city="Test City",
            state="Test State",
            payment_method="Cash on Delivery",
            delivery_proof_path="uploads/proofs/test_dummy_proof.jpg",
            customer_signature_path="uploads/signatures/test_dummy_sig.png"
        )
        self.db.add(order)
        self.db.commit()

        # 2. Add related child records
        item = OrderItem(order_id=test_order_id, product_id=None, quantity=1, price=100)
        tracking = DeliveryTracking(order_id=test_order_id, status="Cancelled", remarks="Test cancel")
        payment = Payment(order_id=test_order_id, user_id=self.user_id, payment_method="Cash on Delivery", amount=100, screenshot_path="uploads/payments/test_pay.jpg")
        proof = DeliveryProof(order_id=test_order_id, image_path="uploads/proofs/test_dummy_proof.jpg", signature_path="uploads/signatures/test_dummy_sig.png")
        notif = Notification(user_id=self.user_id, title="Order Cancelled", message=f"Your order {test_order_id} has been cancelled.", type="order")

        self.db.add_all([item, tracking, payment, proof, notif])
        self.db.commit()

        # Verify all records exist before deletion
        self.assertIsNotNone(self.db.query(Order).filter(Order.order_id == test_order_id).first())
        self.assertEqual(self.db.query(OrderItem).filter(OrderItem.order_id == test_order_id).count(), 1)
        self.assertEqual(self.db.query(DeliveryTracking).filter(DeliveryTracking.order_id == test_order_id).count(), 1)
        self.assertEqual(self.db.query(Payment).filter(Payment.order_id == test_order_id).count(), 1)
        self.assertEqual(self.db.query(DeliveryProof).filter(DeliveryProof.order_id == test_order_id).count(), 1)
        self.assertEqual(self.db.query(Notification).filter(Notification.message.like(f"%{test_order_id}%")).count(), 1)

        # 3. Call delete_order via admin
        res = delete_order(
            order_id=test_order_id,
            admin_email=self.test_admin_email,
            x_admin_email=None,
            db=self.db
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["order_id"], test_order_id)
        self.assertEqual(res["notifications_removed"], 1)

        # 4. Verify all records have been cleanly deleted
        self.assertIsNone(self.db.query(Order).filter(Order.order_id == test_order_id).first())
        self.assertEqual(self.db.query(OrderItem).filter(OrderItem.order_id == test_order_id).count(), 0)
        self.assertEqual(self.db.query(DeliveryTracking).filter(DeliveryTracking.order_id == test_order_id).count(), 0)
        self.assertEqual(self.db.query(Payment).filter(Payment.order_id == test_order_id).count(), 0)
        self.assertEqual(self.db.query(DeliveryProof).filter(DeliveryProof.order_id == test_order_id).count(), 0)
        self.assertEqual(self.db.query(Notification).filter(Notification.message.like(f"%{test_order_id}%")).count(), 0)
        print(" [PASS] Full cascade order deletion verified successfully.")

    def test_order_deletion_without_hash_prefix(self):
        """Verify order can be deleted even if client omits the leading '#' in order_id."""
        test_order_id = "#PLT_TEST_NO_HASH_102"
        order = Order(
            order_id=test_order_id,
            user_id=self.user_id,
            date="16 Sep 2026, 03:00 AM",
            status="Cancelled",
            subtotal=50,
            delivery_charge=0,
            total_amount=50,
            full_name="Test Customer",
            phone_number="1234567890",
            pincode="123456",
            address_line="Test Address",
            city="Test City",
            state="Test State",
            payment_method="Cash on Delivery"
        )
        self.db.add(order)
        self.db.commit()

        # Call delete_order using "PLT_TEST_NO_HASH_102" (without '#')
        res = delete_order(
            order_id="PLT_TEST_NO_HASH_102",
            admin_email=self.test_admin_email,
            db=self.db
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["order_id"], test_order_id)
        self.assertIsNone(self.db.query(Order).filter(Order.order_id == test_order_id).first())
        print(" [PASS] Order deletion without hash prefix verified.")

    def test_transaction_rollback_on_failure(self):
        """Verify that any database failure triggers a rollback and preserves original data."""
        test_order_id = "#PLT_TEST_ROLLBACK_103"
        order = Order(
            order_id=test_order_id,
            user_id=self.user_id,
            date="16 Sep 2026, 03:00 AM",
            status="Cancelled",
            subtotal=50,
            delivery_charge=0,
            total_amount=50,
            full_name="Test Customer",
            phone_number="1234567890",
            pincode="123456",
            address_line="Test Address",
            city="Test City",
            state="Test State",
            payment_method="Cash on Delivery"
        )
        notif = Notification(user_id=self.user_id, title="Alert", message=f"Order {test_order_id} pending", type="order")
        self.db.add_all([order, notif])
        self.db.commit()

        # Mock db.delete to fail and raise an exception
        original_delete = self.db.delete
        def failing_delete(instance):
            if isinstance(instance, Order) and instance.order_id == test_order_id:
                raise RuntimeError("Simulated database failure during order delete")
            return original_delete(instance)

        self.db.delete = failing_delete

        try:
            with self.assertRaises(HTTPException) as cm:
                delete_order(
                    order_id=test_order_id,
                    admin_email=self.test_admin_email,
                    db=self.db
                )
            self.assertEqual(cm.exception.status_code, 500)
            self.assertIn("Simulated database failure", cm.exception.detail)
        finally:
            self.db.delete = original_delete

        # Verify order and notification were NOT deleted due to rollback
        reloaded_order = self.db.query(Order).filter(Order.order_id == test_order_id).first()
        reloaded_notif = self.db.query(Notification).filter(Notification.message.like(f"%{test_order_id}%")).first()
        self.assertIsNotNone(reloaded_order, "Order should still exist after rollback")
        self.assertIsNotNone(reloaded_notif, "Notification should still exist after rollback")

        # Cleanup
        self.db.delete(reloaded_notif)
        self.db.delete(reloaded_order)
        self.db.commit()
        print(" [PASS] Transaction rollback on failure verified.")

if __name__ == "__main__":
    unittest.main()
