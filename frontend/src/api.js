// Nova API utility (mock implementation, ready for real endpoints)

const API_BASE = 'http://localhost:8000'; // Change if backend is hosted elsewhere

export async function getMessages(session_id) {
  const url = session_id ? `${API_BASE}/messages?session_id=${session_id}` : `${API_BASE}/messages`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch messages');
  return await res.json();
}

export async function postMessage(message) {
  const res = await fetch(`${API_BASE}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return await res.json();
}

export async function getSummaries(session_id) {
  const url = session_id ? `${API_BASE}/summary?session_id=${session_id}` : `${API_BASE}/summary`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch summaries');
  return await res.json();
}

export async function generateSummary(session_id) {
  const res = await fetch(`${API_BASE}/generate-summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id }),
  });
  if (!res.ok) throw new Error('Failed to generate summary');
  return await res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to create session');
  return await res.json();
}

export async function sendChatMessage({ user_message, local_history, session_id, topic }) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_message, local_history, session_id, topic }),
  });
  if (!res.ok) throw new Error('Failed to send chat message');
  return await res.json();
}

export async function* sendChatMessageStream({ user_message, local_history, session_id, topic }) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_message, local_history, session_id, topic }),
  });
  if (!res.ok) throw new Error('Failed to send chat message');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let done = false;
  let buffer = '';
  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;
    if (value) {
      buffer = decoder.decode(value, { stream: true });
      yield buffer;
    }
  }
}

export async function getGeminiContext(session_id, topic) {
  const res = await fetch(`${API_BASE}/gemini/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, topic }),
  });
  if (!res.ok) throw new Error('Failed to fetch Gemini context');
  return await res.json();
} 