from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend import firebase, models, llm, session
from typing import List, Optional

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