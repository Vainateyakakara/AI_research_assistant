export default function LoadingSpinner({ mode }) {
  const messages = {
    simple: '⚡ Generating quick answer…',
    analysis: '📊 Retrieving from local DB and analysing with Gemini…',
    research: '🔬 Searching arXiv, downloading papers, indexing & retrieving… (this may take ~30–60s)',
  };

  return (
    <div className="loading-container">
      <div className="spinner"></div>
      <div className="loading-text">{messages[mode] || 'Processing…'}</div>
    </div>
  );
}
