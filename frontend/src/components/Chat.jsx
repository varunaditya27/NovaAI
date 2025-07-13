import { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import SummarySidebar from './SummarySidebar';
import './Chat.css';
import { getMessages, getSummaries, generateSummary, createSession, sendChatMessageStream } from '../api';

const CHAT_HISTORY_KEY = 'nova_chat_history';
const SESSION_TIMEOUT_MINUTES = 30; // Example: 30 minutes

function getSessionIdFromStorage() {
  return localStorage.getItem('nova_session_id');
}
function setSessionIdToStorage(id) {
  localStorage.setItem('nova_session_id', id);
}
function getChatHistoryFromStorage() {
  const raw = localStorage.getItem(CHAT_HISTORY_KEY);
  return raw ? JSON.parse(raw) : [];
}
function setChatHistoryToStorage(history) {
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(history));
}
function clearChatHistory() {
  localStorage.removeItem(CHAT_HISTORY_KEY);
}

export default function Chat() {
  const [sessionId, setSessionId] = useState(getSessionIdFromStorage() || null);
  const [messages, setMessages] = useState(getChatHistoryFromStorage());
  const [isTyping, setIsTyping] = useState(false);
  const [quotedMessage, setQuotedMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [summaries, setSummaries] = useState([]);
  const [showSummary, setShowSummary] = useState(false);
  const chatRef = useRef(null);

  // On mount, fetch all messages from backend (across all sessions)
  useEffect(() => {
    setLoading(true);
    getMessages() // No session_id: fetches all messages
      .then(msgs => {
        setMessages(msgs);
        setChatHistoryToStorage(msgs);
        setLoading(false);
      })
      .catch(e => {
        setError('Failed to load messages.');
        setLoading(false);
      });
    let sid = getSessionIdFromStorage();
    if (!sid) {
      createSession().then(session => {
        sid = session.session_id;
        setSessionIdToStorage(sid);
        setSessionId(sid);
      });
    } else {
      setSessionId(sid);
    }
  }, []);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // Handler for sending a new message
  const handleSend = async (text) => {
    if (!text.trim()) return;
    let sid = sessionId;
    if (!sid) {
      try {
        const session = await createSession();
        sid = session.session_id;
        setSessionIdToStorage(sid);
        setSessionId(sid);
      } catch (e) {
        setError('Failed to create session.');
        return;
      }
    }
    // Prepare new user message
    const now = new Date();
    const newMsg = {
      session_id: sid,
      text,
      tags: [],
      mood: 'user',
      timestamp: now.toISOString(),
      ...(quotedMessage ? {
        quoted_reply_to: quotedMessage.message_id,
        quoted_text: quotedMessage.text,
      } : {}),
    };
    setIsTyping(true);
    setQuotedMessage(null);
    // Optimistically add user message to chat and localStorage
    const optimisticMsgs = [...getChatHistoryFromStorage(), newMsg];
    setMessages(optimisticMsgs);
    setChatHistoryToStorage(optimisticMsgs);
    try {
      // Streaming Groq reply
      let novaMsg = {
        session_id: sid,
        text: '',
        tags: [],
        mood: 'nova',
        timestamp: new Date().toISOString(),
      };
      setMessages([...optimisticMsgs, novaMsg]);
      setChatHistoryToStorage([...optimisticMsgs, novaMsg]);
      let streamedText = '';
      for await (const chunk of sendChatMessageStream({
        user_message: text,
        local_history: optimisticMsgs,
        session_id: sid,
      })) {
        streamedText += chunk;
        novaMsg.text = streamedText;
        setMessages([...optimisticMsgs, { ...novaMsg }]);
        setChatHistoryToStorage([...optimisticMsgs, { ...novaMsg }]);
      }
      // After sending, fetch all messages again to ensure full history is up to date
      const allMsgs = await getMessages();
      setMessages(allMsgs);
      setChatHistoryToStorage(allMsgs);
      setIsTyping(false);
    } catch (e) {
      setError('Failed to send message.');
      setIsTyping(false);
      // Optionally, remove optimistic message on error
      const filtered = getChatHistoryFromStorage().filter(m => m.timestamp !== newMsg.timestamp);
      setMessages(filtered);
      setChatHistoryToStorage(filtered);
    }
  };

  // Handler for quoting a message
  const handleQuote = (msg) => setQuotedMessage(msg);

  // Scroll to quoted message
  const handleScrollToMessage = (messageId) => {
    const el = document.getElementById(`msg-${messageId}`);
    if (el && chatRef.current) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('nova-highlight');
      setTimeout(() => el.classList.remove('nova-highlight'), 1200);
    }
  };

  return (
    <div className="nova-chat-container">
      <div className="nova-chat-header">
        <div className="nova-header-avatar">🪐</div>
        <div className="nova-header-title">NOVA</div>
        <div className="nova-header-status">Online</div>
      </div>
      <div className="nova-chat-messages" ref={chatRef}>
        <button className="nova-summary-toggle" onClick={() => setShowSummary(s => !s)} aria-label="Show summaries">📝</button>
        {loading ? (
          <div className="nova-loading">Loading messages...</div>
        ) : error ? (
          <div className="nova-error">{error}</div>
        ) : (
          <MessageList messages={messages} onQuote={handleQuote} onScrollToMessage={handleScrollToMessage} />
        )}
        {isTyping && <TypingIndicator />}
      </div>
      <MessageInput onSend={handleSend} quotedMessage={quotedMessage} onCancelQuote={() => setQuotedMessage(null)} />
    </div>
  );
} 