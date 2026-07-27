import firebase_admin
from firebase_admin import credentials, messaging
import os
from database.connection import get_db
from models.user import User, Admin
from sqlalchemy.orm import Session

# Initialize Firebase Admin SDK
cred_path = "serviceAccountKey.json"
if os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        FCM_ENABLED = True
        print("Firebase Admin initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Firebase Admin: {e}")
        FCM_ENABLED = False
else:
    print(f"Firebase credentials not found at {cred_path}. FCM Push Notifications are disabled.")
    FCM_ENABLED = False

def send_push_notification(email: str, title: str, body: str, notif_type: str = "system", role: str = "customer"):
    """
    Sends a push notification to a specific user or admin.
    """
    db: Session = next(get_db())
    fcm_token = None
    
    if role == "admin":
        admin = db.query(Admin).filter(Admin.email == email).first()
        if admin:
            fcm_token = admin.fcm_token
    else:
        user = db.query(User).filter(User.email == email).first()
        if user:
            fcm_token = user.fcm_token
            
    if not fcm_token:
        print(f"No FCM token found for {role} {email}")
        return False
        
    if not FCM_ENABLED:
        print(f"Mock FCM Push to {email}: Title: '{title}', Body: '{body}'")
        return True

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                "title": title,
                "message": body,
                "type": notif_type
            },
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Successfully sent message to {email}: {response}")
        return True
    except Exception as e:
        print(f"Error sending message to {email}: {e}")
        return False

def send_push_notification_to_all_admins(title: str, body: str, notif_type: str = "system"):
    """
    Sends a push notification to all admins.
    """
    db: Session = next(get_db())
    admins = db.query(Admin).all()
    for admin in admins:
        if admin.fcm_token:
            if not FCM_ENABLED:
                print(f"Mock FCM Push to Admin {admin.email}: Title: '{title}', Body: '{body}'")
                continue
            
            try:
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={"title": title, "message": body, "type": notif_type},
                    token=admin.fcm_token,
                )
                messaging.send(message)
                print(f"Successfully sent admin message to {admin.email}")
            except Exception as e:
                print(f"Error sending admin message to {admin.email}: {e}")
