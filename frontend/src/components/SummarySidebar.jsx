import './SummarySidebar.css';

export default function SummarySidebar({ open, onClose, summaries, onGenerate, loading }) {
  return (
    <div className={`nova-summary-sidebar${open ? ' open' : ''}`} role="complementary" aria-label="Session Summaries">
      <button className="nova-summary-close" onClick={onClose} aria-label="Close summaries">✕</button>
      <h2 className="nova-summary-title">Session Summaries</h2>
      <button className="nova-summary-generate" onClick={onGenerate} disabled={loading} aria-label="Generate summary">Generate Summary</button>
      <div className="nova-summary-list">
        {loading ? (
          <div className="nova-summary-loading">Loading...</div>
        ) : summaries && summaries.length > 0 ? (
          summaries.map((s, i) => (
            <div className="nova-summary-item" key={i}>
              <div className="nova-summary-date">{new Date(s.timestamp).toLocaleString()}</div>
              <ul className="nova-summary-bullets">
                {s.summary.map((pt, j) => <li key={j}>{pt}</li>)}
              </ul>
              <div className="nova-summary-topics">Topics: {s.topics.join(', ')}</div>
            </div>
          ))
        ) : (
          <div className="nova-summary-empty">No summaries yet.</div>
        )}
      </div>
    </div>
  );
} 