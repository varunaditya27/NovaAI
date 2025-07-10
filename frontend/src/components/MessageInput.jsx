import { useState } from 'react';
import './MessageInput.css';

export default function MessageInput({ onSend, quotedMessage, onCancelQuote }) {
  const [text, setText] = useState('');
  const handleSend = () => {
    if (text.trim()) {
      onSend(text);
      setText('');
    }
  };
  return (
    <div className="nova-message-input">
      {quotedMessage && (
        <div className="nova-quoted-preview">
          <span className="nova-quoted-bar" />
          <span className="nova-quoted-text">{quotedMessage.text}</span>
          <button className="nova-cancel-quote" onClick={onCancelQuote} title="Cancel quote">✕</button>
        </div>
      )}
      <textarea
        className="nova-input-textarea"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Type a message..."
        rows={1}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
      />
      <button className="nova-send-btn" onClick={handleSend} disabled={!text.trim()}>
        <span style={{fontSize: '1.2em', marginRight: '0.2em'}}>✈️</span> Send
      </button>
    </div>
  );
} 