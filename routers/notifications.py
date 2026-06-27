from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database.connection import get_db
from models.interaction import Notification
from models.user import User
from schemas.interaction import NotificationResponse
from typing import List, Optional
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        text_data = json.dumps(message)
        # Iterate over a copy to avoid issues if connections are removed
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/admin")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # If admin or unregistered, return only system notifications
        return db.query(Notification).filter(Notification.user_id.is_(None)).order_by(Notification.created_at.desc()).all()
        
    # Get user specific + general system notifications
    return db.query(Notification).filter(
        (Notification.user_id == user.id) | (Notification.user_id.is_(None))
    ).order_by(Notification.created_at.desc()).all()

@router.put("/notifications/{notif_id}/read")
def mark_as_read(notif_id: int, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = True
    db.commit()
    return {"status": "success", "message": "Notification marked as read"}
