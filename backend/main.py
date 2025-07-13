from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import threading
from backend import firebase, models, llm
from typing import List, Optional
from backend.models import Thread, Message
import datetime

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/messages", response_model=List[models.Message])
def get_messages(session_id: Optional[str] = Query(None)):
    try:
        return firebase.get_messages(session_id=session_id)
    except Exception as e:
        print("ERROR in /messages:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/message", response_model=List[models.Message])
def post_message(msg: models.MessageCreate):
    print("POST /message called with :", msg)
    try:
        # Save user message
        user_msg = firebase.save_message(msg)
        # Generate Nova reply using Groq
        prompt = msg.text
        nova_reply_text = llm.generate_dialog_response(prompt)
        nova_msg = firebase.save_message(models.MessageCreate(
            session_id=user_msg.session_id,
            text=nova_reply_text,
            quoted_reply_to=user_msg.message_id,
            quoted_text=user_msg.text,
            tags=[],
            mood="nova",
        ))
        return [user_msg, nova_msg]
    except Exception as e:
        print("ERROR in /message:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/threads/cluster", response_model=List[Thread])
def cluster_threads(session_id: str):
    messages = firebase.get_messages(session_id=session_id)
    clusters = llm.cluster_messages_by_topic_gemini(messages)
    threads = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()  # Convert to string
    for idx, cluster in enumerate(clusters):
        thread = Thread(
            thread_id=f"{session_id}-thread-{idx}",
            topic=f"Topic {idx+1}",  # Optionally use topic detection
            messages=cluster,
            created_at=now,
            updated_at=now
        )
        firebase.save_thread(thread)
        threads.append(thread)
    return threads

@app.get("/threads", response_model=List[Thread])
def get_all_threads():
    return firebase.get_all_threads()

@app.get("/threads/by-topic", response_model=List[Thread])
def get_threads_by_topic(topic: str):
    return firebase.get_threads_by_topic(topic)

@app.post("/message-smart", response_model=List[Message])
def post_message_smart(msg: models.MessageCreate):
    # Save user message
    user_msg = firebase.save_message(msg)
    # Fetch relevant thread context using topic clustering
    all_msgs = firebase.get_messages(session_id=user_msg.session_id)
    clusters = llm.cluster_messages_by_topic_gemini(all_msgs)
    # Find the first cluster as the best thread (fallback)
    best_thread = clusters[0] if clusters else []
    context = "\n".join([getattr(m, 'text', '') for m in best_thread if hasattr(m, 'text')]) if best_thread else ""
    # Use Gemini for extra context if needed (e.g., if context is sparse)
    if not context or len(best_thread) < 2:
        summary = llm.generate_summary(user_msg.session_id)
        context += "\n" + "\n".join(summary.summary)
    # Compose prompt for Groq (Llama)
    prompt = f"Context: {context}\nUser: {msg.text}"
    nova_reply_text = llm.generate_dialog_response(prompt)
    # Post-process for human-like texting (simple version)
    if nova_reply_text:
        nova_reply_text = nova_reply_text.replace("\n", " ").strip()
    nova_msg = firebase.save_message(models.MessageCreate(
        session_id=user_msg.session_id,
        text=nova_reply_text,
        quoted_reply_to=user_msg.message_id,
        quoted_text=user_msg.text,
        tags=[],
        mood="nova",
    ))
    return [user_msg, nova_msg]

@app.get("/summary", response_model=List[models.SessionSummary])
def get_summary(session_id: Optional[str] = Query(None)):
    try:
        return firebase.get_summaries(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-summary", response_model=models.SessionSummary)
def generate_summary(session_id: str):
    try:
        return llm.generate_summary(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session", response_model=models.Session)
def create_session():
    try:
        new_session = firebase.get_active_session()
        return new_session
    except Exception as e:
        print("ERROR in /session:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
def chat_stream(
    user_message: str = Body(...),
    local_history: list = Body(...),
    session_id: str = Body(...)
):
    """
    Streaming chat endpoint:
    1. Streams Groq's reply as it is generated.
    2. After streaming, Gemini analyzes and stores the conversation in the background.
    """
    context = "\n".join([f"User: {m['text']}" if m.get('mood', 'user') == 'user' else f"Nova: {m['text']}" for m in local_history])
    prompt = f"{context}\nUser: {user_message}"
    stream = llm.generate_dialog_response_stream(prompt)

    def background_gemini():
        # Wait for the full reply to be streamed, then analyze/store
        full_reply = "".join([chunk for chunk in llm.generate_dialog_response_stream(prompt)])
        try:
            llm.gemini_analyze_and_store(user_message, full_reply, session_id)
        except Exception as e:  # More specific exception can be used if known
            print(f"Gemini background error: {e}")

    threading.Thread(target=background_gemini, daemon=True).start()
    return StreamingResponse(stream, media_type="text/plain")

@app.post("/gemini/context")
def gemini_context(session_id: str = Body(...), topic: str = Body(...)):
    """
    Returns Gemini-generated summary/context for a given topic and session.
    """
    return {"context": llm.get_gemini_context(session_id, topic)}