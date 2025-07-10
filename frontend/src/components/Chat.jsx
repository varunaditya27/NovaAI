import { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';
import SummarySidebar from './SummarySidebar';
import './Chat.css';
import { getMessages, postMessage, getSummaries, generateSummary, createSession } from '../api';

function getSessionIdFromStorage() {
  return localStorage.getItem('nova_session_id');
}
function setSessionIdToStorage(id) {
  localStorage.setItem('nova_session_id', id);
}

export default function Chat() {
  const [sessionId, setSessionId] = useState(getSessionIdFromStorage() || null);
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [quotedMessage, setQuotedMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summaries, setSummaries] = useState([]);
  const [showSummary, setShowSummary] = useState(false);
  const chatRef = useRef(null);

  // Fetch all messages on mount
  useEffect(() => {
    async function fetchAllMessages() {
      setLoading(true);
      setError(null);
      try {
        // Always fetch all messages (across all sessions)
        const msgs = await getMessages();
        // Sort messages by timestamp ascending
        msgs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        setMessages(msgs);
        // Session logic only for sending messages
        let sid = getSessionIdFromStorage();
        if (!sid) {
          const session = await createSession();
          sid = session.session_id;
          setSessionIdToStorage(sid);
          setSessionId(sid);
        } else {
          setSessionId(sid);
        }
        setLoading(false);
      } catch (e) {
        setError('Failed to load messages.');
        setLoading(false);
      }
    }
    fetchAllMessages();
    // eslint-disable-next-line
  }, []);

  // Fetch summaries for the session
  useEffect(() => {
    if (!sessionId) return;
    getSummaries(sessionId)
      .then(setSummaries)
      .catch(() => setSummaries([]));
  }, [sessionId]);

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
    // If no sessionId, create a new session first
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
    const newMsg = {
      session_id: sid,
      text,
      tags: [],
      mood: 'user',
      ...(quotedMessage ? {
        quoted_reply_to: quotedMessage.message_id,
        quoted_text: quotedMessage.text,
      } : {}),
    };
    setIsTyping(true);
    setQuotedMessage(null);
    // Optimistically add user message to chat
    const tempId = `temp-${Date.now()}`;
    const optimisticMsg = {
      ...newMsg,
      message_id: tempId,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, optimisticMsg]);
    try {
      // /message now returns [userMsg, novaMsg]
      const msgs = await postMessage(newMsg);
      // Replace optimistic user message with real one, then add Nova's reply
      setMessages(prev => [
        ...prev.filter(m => m.message_id !== tempId),
        ...msgs
      ]);
      setIsTyping(false);
    } catch (e) {
      setError('Failed to send message.');
      setIsTyping(false);
      // Optionally, remove optimistic message on error
      setMessages(prev => prev.filter(m => m.message_id !== tempId));
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

  // Generate summary for the session
  const handleGenerateSummary = async () => {
    if (!sessionId) return;
    try {
      await generateSummary(sessionId);
      const updated = await getSummaries(sessionId);
      setSummaries(updated);
    } catch (e) {
      setError('Failed to generate summary.');
    }
  };

  return (
    <div className="nova-chat-container">
      <div className="nova-chat-header">
        <div className="nova-header-avatar">🪐</div>
        <div className="nova-header-title">NOVA</div>
        <div className="nova-header-status">Online</div>
      </div>
      <SummarySidebar
        open={showSummary}
        onClose={() => setShowSummary(false)}
        summaries={summaries}
        onGenerate={handleGenerateSummary}
        loading={!summaries}
      />
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