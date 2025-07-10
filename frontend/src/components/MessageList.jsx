import MessageBubble from './MessageBubble';
import TimeBreak from './TimeBreak';
import './MessageList.css';

// Helper to insert time breaks
function insertTimeBreaks(messages) {
  if (!messages.length) return [];
  const result = [];
  let lastDate = null;
  const now = new Date();
  messages.forEach((msg, i) => {
    const msgDate = new Date(msg.timestamp);
    let label = null;
    if (!lastDate || msgDate.toDateString() !== lastDate.toDateString()) {
      const diff = (now - msgDate) / (1000 * 60 * 60 * 24);
      if (diff < 1) label = 'Today';
      else if (diff < 2) label = 'Yesterday';
      else if (diff < 7) label = msgDate.toLocaleDateString(undefined, { weekday: 'long' });
      else label = msgDate.toLocaleDateString();
    }
    if (label) result.push({ type: 'break', label, key: `break_${msg.message_id}` });
    result.push({ type: 'msg', ...msg });
    lastDate = msgDate;
  });
  return result;
}

export default function MessageList({ messages, onQuote, onScrollToMessage }) {
  const items = insertTimeBreaks(messages);
  return (
    <div className="nova-message-list">
      {items.map(item =>
        item.type === 'break' ? (
          <TimeBreak key={item.key} label={item.label} />
        ) : (
          <MessageBubble
            key={item.message_id}
            message={item}
            onQuote={onQuote}
            onScrollToMessage={onScrollToMessage}
            id={`msg-${item.message_id}`}
          />
        )
      )}
    </div>
  );
} 