from backend import models
from typing import List, Optional
import uuid
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# --- Topic Logic ---
def upsert_topic_session_summary(topic: str, session_id: str, summary: list, timestamp: str, message_ids: list):
    """
    Upserts a topic document in /topics/{topic} with a new session summary.
    If the topic exists, appends to the sessions array. If not, creates it.
    Each session summary includes session_id, summary, timestamp, message_ids.
    """
    topic_ref = db.collection("topics").document(topic)
    doc = topic_ref.get()
    session_obj = {
        "session_id": session_id,
        "summary": summary,
        "timestamp": timestamp,
        "message_ids": message_ids or [],
    }
    if doc.exists:
        data = doc.to_dict()
        sessions = data.get("sessions", [])
        # Prevent duplicate session summaries
        if not any(s["session_id"] == session_id for s in sessions):
            sessions.append(session_obj)
            topic_ref.update({"sessions": sessions})
            logger.info(f"Appended session summary to topic '{topic}' for session {session_id}")
    else:
        topic_ref.set({
            "topic": topic,
            "sessions": [session_obj]
        })
        logger.info(f"Created topic '{topic}' with first session summary {session_id}")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nova-firebase")

# Read credentials path from environment variables
cred_path = os.environ.get("YOUR_FIREBASE_CREDENTIALS_JSON")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

SESSION_TIMEOUT_HOURS = 2

# --- Session Logic ---
def get_active_session() -> models.Session:
    """
    Returns the most recent active session (within SESSION_TIMEOUT_HOURS), or creates a new one.
    Always uses UTC for timestamps. Logs session creation and retrieval.
    """
    sessions_ref = db.collection("sessions").order_by("last_activity", direction=firestore.Query.DESCENDING).limit(1)
    docs = list(sessions_ref.stream())
    now = datetime.now(timezone.utc)
    if docs:
        session = docs[0].to_dict()
        last_activity = datetime.fromisoformat(session["last_activity"])
        diff_hours = (now - last_activity).total_seconds() / 3600
        if diff_hours < SESSION_TIMEOUT_HOURS:
            logger.info(f"Returning active session {session['session_id']} (last activity {last_activity}, {diff_hours:.2f}h ago)")
            return models.Session(**session)
        else:
            logger.info(f"Session {session['session_id']} expired ({diff_hours:.2f}h since last activity). Creating new session.")
            # Analyze the just-ended session for topic summaries
            try:
                from backend import llm
                llm.gemini_analyze_session_topics(session["session_id"])
            except Exception as e:
                logger.error(f"Failed to analyze session topics for session {session['session_id']}: {e}")
    # Create new session
    session_id = str(uuid.uuid4())
    session_obj = models.Session(
        session_id=session_id,
        created_at=now.isoformat(),
        last_activity=now.isoformat(),
    )
    db.collection("sessions").document(session_id).set(session_obj.model_dump())
    logger.info(f"Created new session {session_id} at {now.isoformat()}")
    return session_obj

def update_session_activity(session_id: str):
    """
    Updates the last_activity timestamp for a session to now (UTC ISO format).
    """
    now = datetime.now(timezone.utc).isoformat()
    db.collection("sessions").document(session_id).update({"last_activity": now})
    logger.info(f"Updated session {session_id} last_activity to {now}")

# --- Message Logic ---
def get_messages(session_id: Optional[str] = None) -> List[models.Message]:
    """
    Returns all messages for a session (chronological), or all messages if session_id is None.
    """
    if session_id:
        msgs_ref = db.collection("messages").where("session_id", "==", session_id).order_by("timestamp")
    else:
        msgs_ref = db.collection("messages").order_by("timestamp")
    messages = [models.Message(**doc.to_dict()) for doc in msgs_ref.stream()]
    logger.info(f"Fetched {len(messages)} messages for session {session_id}")
    return messages

def save_message(msg: models.MessageCreate) -> models.Message:
    """
    Saves a message to Firestore, ensuring session is valid and last_activity is updated.
    Returns the saved Message object.
    """
    # Determine session
    if msg.session_id:
        session_id = msg.session_id
    else:
        session = get_active_session()
        session_id = session.session_id
    now = datetime.now(timezone.utc).isoformat()
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
    db.collection("messages").document(message_id).set(message.model_dump())
    update_session_activity(session_id)
    logger.info(f"Saved message {message_id} to session {session_id} at {now}")
    return message

# --- Summary Logic ---
def get_summaries(session_id: Optional[str] = None) -> List[models.SessionSummary]:
    if session_id:
        summaries_ref = db.collection("summaries").where("session_id", "==", session_id).order_by("timestamp")
    else:
        summaries_ref = db.collection("summaries").order_by("timestamp")
    summaries = [models.SessionSummary(**doc.to_dict()) for doc in summaries_ref.stream()]
    logger.info(f"Fetched {len(summaries)} summaries for session {session_id}")
    return summaries

def save_summary(summary: models.SessionSummary):
    db.collection("summaries").add(summary.model_dump())
    logger.info(f"Saved summary for session {summary.session_id} at {summary.timestamp}")

def save_thread(thread: models.Thread):
    db.collection("threads").document(thread.thread_id).set(thread.model_dump())
    logger.info(f"Saved thread {thread.thread_id} (topic: {thread.topic})")

def get_threads_by_topic(topic: str):
    threads_ref = db.collection("threads").where("topic", "==", topic)
    threads = [models.Thread(**doc.to_dict()) for doc in threads_ref.stream()]
    logger.info(f"Fetched {len(threads)} threads for topic '{topic}'")
    return threads

def get_all_threads():
    threads_ref = db.collection("threads")
    threads = [models.Thread(**doc.to_dict()) for doc in threads_ref.stream()]
    logger.info(f"Fetched {len(threads)} threads (all topics)")
    return threads