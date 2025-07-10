import './QuotedReply.css';

export default function QuotedReply({ text, quotedId, onScrollToMessage }) {
  const clickable = !!onScrollToMessage && !!quotedId;
  return (
    <div
      className={`nova-quoted-reply${clickable ? ' clickable' : ''}`}
      onClick={clickable ? () => onScrollToMessage(quotedId) : undefined}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={clickable ? 'Scroll to quoted message' : undefined}
      style={clickable ? { cursor: 'pointer' } : {}}
    >
      <span className="nova-quoted-bar" />
      <span className="nova-quoted-text">{text}</span>
    </div>
  );
} 