import requests
import sys
import os

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

ADMIN_EMAIL = "admin@plantora.com"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(label, condition, extra=""):
    status = "[PASS]" if condition else "[FAIL]"
    print(f"  {status} {label} {extra}")
    return condition

def test_get_notifications(email, label=""):
    r = requests.get(f"{BASE_URL}/api/notifications", params={"email": email})
    check(f"GET /notifications ({label})", r.status_code == 200, f"-> status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"          Returned {len(data)} notifications")
        return data
    return []

def test_unread_count(email, label=""):
    r = requests.get(f"{BASE_URL}/api/notifications/unread-count", params={"email": email})
    check(f"GET /notifications/unread-count ({label})", r.status_code == 200, f"-> status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"          Unread count: {data.get('unread_count', '?')}")
        return data.get("unread_count", 0)
    return -1

def test_mark_read(notif_id):
    r = requests.put(f"{BASE_URL}/api/notifications/{notif_id}/read")
    return check(f"PUT /notifications/{notif_id}/read", r.status_code == 200, f"-> {r.json()}")

def test_delete_single(notif_id):
    r = requests.delete(f"{BASE_URL}/api/notifications/{notif_id}")
    return check(f"DELETE /notifications/{notif_id}", r.status_code == 200, f"-> {r.json()}")

def test_clear_notifications(email, label=""):
    r = requests.delete(f"{BASE_URL}/api/notifications/clear", params={"email": email})
    return check(f"DELETE /notifications/clear ({label})", r.status_code == 200, f"-> {r.json() if r.status_code == 200 else r.text}")

def test_register_fcm_token(email, token):
    r = requests.post(f"{BASE_URL}/api/auth/fcm-token", params={"email": email, "token": token})
    return check(f"POST /auth/fcm-token (email={email})", r.status_code == 200, f"-> {r.json() if r.status_code == 200 else r.text}")

# ============================================================
#  TEST 1: Get Notifications
# ============================================================
section("TEST 1: GET Notifications")
notifs = test_get_notifications(ADMIN_EMAIL, "admin")

# ============================================================
#  TEST 2: Unread Count
# ============================================================
section("TEST 2: Unread Count Endpoint")
count_before = test_unread_count(ADMIN_EMAIL, "admin before clear")

# ============================================================
#  TEST 3: Mark single notification as read (if any exist)
# ============================================================
section("TEST 3: Mark Single Notification as Read")
if notifs:
    unread = [n for n in notifs if not n.get("is_read", True)]
    if unread:
        test_mark_read(unread[0]["id"])
        count_after_read = test_unread_count(ADMIN_EMAIL, "admin after marking 1 read")
        check("Unread count decreased by 1", count_after_read == count_before - 1, f"({count_before} -> {count_after_read})")
    else:
        print("  [SKIP] No unread notifications to test")
else:
    print("  [SKIP] No notifications found")

# ============================================================
#  TEST 4: Delete Single Notification
# ============================================================
section("TEST 4: Delete Single Notification")
if notifs:
    test_delete_single(notifs[0]["id"])
    notifs_after = test_get_notifications(ADMIN_EMAIL, "after single delete")
    check("Notification count decreased", len(notifs_after) < len(notifs), f"({len(notifs)} -> {len(notifs_after)})")
else:
    print("  [SKIP] No notifications found")

# ============================================================
#  TEST 5: Clear All Notifications
# ============================================================
section("TEST 5: Clear All Notifications (Permanent)")
# First seed a test notification directly via a known order endpoint
# Instead verify the clear endpoint works and then re-fetching returns 0
test_clear_notifications(ADMIN_EMAIL, "admin")
notifs_after_clear = test_get_notifications(ADMIN_EMAIL, "admin after clear all")
check("No notifications returned after clear", len(notifs_after_clear) == 0, f"(got {len(notifs_after_clear)} notifications)")

count_after_clear = test_unread_count(ADMIN_EMAIL, "admin after clear")
check("Unread count is 0 after clear", count_after_clear == 0, f"(got {count_after_clear})")

# ============================================================
#  TEST 6: Clear All Does NOT Return Cleared Notifications
# ============================================================
section("TEST 6: Verify Permanence (re-fetch after clear)")
notifs_re = test_get_notifications(ADMIN_EMAIL, "re-fetch after clear")
check("Old notifications do NOT return after re-fetch", len(notifs_re) == 0, f"(got {len(notifs_re)})")

# ============================================================
#  TEST 7: FCM Token Registration
# ============================================================
section("TEST 7: FCM Token Registration")
test_register_fcm_token(ADMIN_EMAIL, "test_fcm_token_admin_123")

# ============================================================
#  TEST 8: Wrong notif_id returns 404
# ============================================================
section("TEST 8: Edge Case - Delete Non-existent Notification")
r = requests.delete(f"{BASE_URL}/api/notifications/999999999")
check("DELETE non-existent notif returns 404", r.status_code == 404, f"-> {r.status_code}")

# ============================================================
#  SUMMARY
# ============================================================
section("SUMMARY")
print("  All API endpoint tests completed. Check [PASS]/[FAIL] above.")
