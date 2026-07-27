import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from models.interaction import Notification
from models.user import Admin

db = SessionLocal()

try:
    count = db.query(Notification).filter(
        Notification.user_id.is_(None)
    ).delete(synchronize_session=False)
    db.commit()
    print("Success, count:", count)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
