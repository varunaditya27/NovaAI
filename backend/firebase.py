from backend import models
from typing import List, Optional
import datetime
import uuid
import os

from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore

# Read credentials path from environment variables
cred_path = os.environ.get("YOUR_FIREBASE_CREDENTIALS_JSON")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

SESSION_TIMEOUT_HOURS = 6

# --- Session Logic ---
def get_active_session() -> models.Session:
    sessions_ref = db.collection("sessions").order_by("last_activity", direction=firestore.Query.DESCENDING).limit(1)
    docs = list(sessions_ref.stream())
    now = datetime.datetime.utcnow()
    if docs:
        session = docs[0].to_dict()
        last_activity = datetime.datetime.fromisoformat(session["last_activity"])
        if (now - last_activity).total_seconds() < SESSION_TIMEOUT_HOURS * 3600:
            return models.Session(**session)
    # Create new session
    session_id = str(uuid.uuid4())
    session_obj = models.Session(
        session_id=session_id,
        created_at=now.isoformat(),
        last_activity=now.isoformat(),
    )
    db.collection("sessions").document(session_id).set(session_obj.dict())
    return session_obj

def update_session_activity(session_id: str):
    now = datetime.datetime.utcnow().isoformat()
    db.collection("sessions").document(session_id).update({"last_activity": now})

# --- Message Logic ---
def get_messages(session_id: Optional[str] = None) -> List[models.Message]:
    if session_id:
        msgs_ref = db.collection("messages").where("session_id", "==", session_id).order_by("timestamp")
    else:
        msgs_ref = db.collection("messages").order_by("timestamp")
    return [models.Message(**doc.to_dict()) for doc in msgs_ref.stream()]

def save_message(msg: models.MessageCreate) -> models.Message:
    # Determine session
    if msg.session_id:
        session_id = msg.session_id
    else:
        session = get_active_session()
        session_id = session.session_id
    now = datetime.datetime.utcnow().isoformat()
    message_id = str(uuid.uuid4())
    message = models.Message(
        message_id=message_id,
        session_id=session_id,
        text=msg.text,
        quoted_reply_to=msg.quoted_reply_to,
        quoted_text=msg.quoted_text,
        timestamp=now,
        tags=msg.tags or [],
        mood=msg.mood or "user",
    )
    db.collection("messages").document(message_id).set(message.dict())
    update_session_activity(session_id)
    return message

# --- Summary Logic ---
def get_summaries(session_id: Optional[str] = None) -> List[models.SessionSummary]:
    if session_id:
        summaries_ref = db.collection("summaries").where("session_id", "==", session_id).order_by("timestamp")
    else:
        summaries_ref = db.collection("summaries").order_by("timestamp")
    return [models.SessionSummary(**doc.to_dict()) for doc in summaries_ref.stream()]

def save_summary(summary: models.SessionSummary):
    db.collection("summaries").add(summary.dict()) 