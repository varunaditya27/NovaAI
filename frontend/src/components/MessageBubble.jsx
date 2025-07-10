import QuotedReply from './QuotedReply';
import './MessageBubble.css';

export default function MessageBubble({ message, onQuote, onScrollToMessage, id }) {
  const isUser = message.mood === 'user' || message.mood === 'excited';
  return (
    <div className={`nova-message-bubble ${isUser ? 'user' : 'nova'}`} id={id}>
      <div className="nova-bubble-avatar">{isUser ? '👤' : '🪐'}</div>
      <div style={{ flex: 1 }}>
        {message.quoted_reply_to && (
          <QuotedReply text={message.quoted_text} quotedId={message.quoted_reply_to} onScrollToMessage={onScrollToMessage} />
        )}
        <div className="nova-message-text">{message.text}</div>
        <div className="nova-message-meta">
          <span className="nova-message-time">{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          <button className="nova-quote-btn" onClick={() => onQuote(message)} title="Quote this message">↩</button>
        </div>
      </div>
    </div>
  );
} 