from backend import models, firebase
import datetime
import os
from dotenv import load_dotenv
import requests
import google.generativeai as genai
import json
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
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
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

def generate_dialog_response_stream(prompt: str):
    """
    Streams Groq's reply token by token using OpenAI-compatible API's stream mode.
    Yields: text chunks as they arrive.
    """
    if not GROQ_API_KEY:
        yield "[Groq API key not set]"
        return
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
            "temperature": 0.7,
            "stream": True
        }
        with requests.post(url, headers=headers, json=data, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        if line.startswith(b'data: '):
                            line = line[6:]
                        if line.strip() == b"[DONE]":
                            break
                        chunk = json.loads(line)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue
    except Exception as e:
        yield f"[Groq API error: {e}]"

def gemini_analyze_and_store(user_message, groq_reply, session_id):
    """
    Gemini acts as the intelligent backend: analyzes the conversation, clusters, and stores relevant info in the DB.
    """
    # Example: Save both user and Groq messages to DB, update threads, etc.
    firebase.save_message(models.MessageCreate(session_id=session_id, text=user_message, mood='user'))
    firebase.save_message(models.MessageCreate(session_id=session_id, text=groq_reply, mood='nova'))
    # Optionally, update threads or summaries here using Gemini logic
    # ...
    return "ok"

def get_gemini_context(session_id, topic):
    """
    Gemini provides a summary/context for a given topic and session.
    """
    # Example: Fetch threads by topic, or generate summary
    threads = firebase.get_threads_by_topic(topic)
    if threads:
        # Return concatenated messages for the topic
        return "\n".join([m.text for t in threads for m in t.messages])
    # Fallback: session summary
    summary = generate_summary(session_id)
    return "\n".join(summary.summary)

def cluster_messages_by_topic_gemini(messages):
    """
    Use Gemini to cluster messages by topic. Returns a list of clusters (each cluster is a list of messages).
    """
    if not messages:
        return []
    chat_text = "\n".join([f"User: {m.text}" if getattr(m, 'mood', 'user') == 'user' else f"Nova: {m.text}" for m in messages])
    prompt = (
        "You are a memory agent for a chat system. Group the following messages into topic-based clusters.\n"
        "Return a JSON list of clusters, where each cluster is a list of message indices (0-based, corresponding to the order below).\n"
        "Messages:\n" + chat_text +
        "\nRespond in strict JSON as: [[0,1],[2,3,4],...]"
    )
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        clusters = json.loads(response.text.strip())
        # Map indices back to messages
        return [[messages[i] for i in cluster] for cluster in clusters]
    except Exception as e:
        return [messages]  # fallback: all in one cluster