from backend import models, firebase
import datetime
import os
from dotenv import load_dotenv
import requests
import google.generativeai as genai
load_dotenv()

GROQ_API_KEY = os.environ.get("YOUR_GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("YOUR_GEMINI_API_KEY")

# --- Gemini Summarization (using google-generativeai SDK) ---
# You can switch to 'models/gemini-1.5-pro-latest' for higher quality if desired
GEMINI_MODEL = 'models/gemini-1.5-flash-latest'

def generate_summary(session_id: str) -> models.SessionSummary:
    messages = firebase.get_messages(session_id=session_id)
    if not messages:
        summary = ["No messages in this session."]
        topics = []
    else:
        chat_text = "\n".join([
            f"User: {m.text}" if m.mood == 'user' else f"Nova: {m.text}" for m in messages
        ])
        prompt = (
            "You are a context-sensitive memory agent for a long-term human-AI chat system.\n"
            "Your goal is to summarize a session of messages exchanged between the user and an assistant named Nova.\n\n"
            "- Extract main discussion points as bullet points\n"
            "- Identify main topics as lowercase strings\n"
            "- NEVER hallucinate content not in the session\n\n"
            "Respond in strict JSON format as:\n"
            "{\n"
            "  \"summary\": [\"...\", \"...\"],\n"
            "  \"topics\": [\"...\"]\n"
            "}\n\n"
            f"Chat:\n{chat_text}"
        )
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            gemini_text = response.text.strip()
            import json
            try:
                parsed = json.loads(gemini_text)
                summary = parsed.get("summary") or [gemini_text]
                topics = parsed.get("topics") or []
            except Exception:
                summary = [gemini_text]
                topics = []
        except Exception as e:
            summary = [f"[Gemini API error: {e}]"]
            topics = []
    summary_obj = models.SessionSummary(
        summary=summary,
        timestamp=datetime.datetime.utcnow().isoformat(),
        topics=topics,
        session_id=session_id,
    )
    firebase.save_summary(summary_obj)
    return summary_obj

# --- Groq LLaMA Dialog ---
# You can switch to another Groq model if desired
GROQ_MODEL = 'llama3-70b-8192'

def generate_dialog_response(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "[Groq API key not set]"
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        system_prompt_text = {
            "role": "system",
            "content": (
                "You are Nova, a helpful, emotionally intelligent, humanlike chatbot. "
                "You sound natural and friendly — like texting with a friend on WhatsApp. "
                "You remember what the user said in past sessions if summaries are provided. "
                "You can quote earlier messages if needed, but NEVER hallucinate.\n\n"
                "Always keep replies appropriately sized — short when the user just needs a nudge or confirmation, "
                "longer when explanation or empathy is needed. "
                "You're aware of time references like 'yesterday', 'last Friday', etc.\n\n"
                "If you're unsure whether something was said before, say so clearly. Don’t make things up."
            )
        }
        data = {
            "model": GROQ_MODEL,
            "messages": [
                system_prompt_text,
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 256,
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
        return reply.strip()
    except Exception as e:
        return f"[Groq API error: {e}]" 