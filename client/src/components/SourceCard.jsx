export default function SourceCard({ source, index, isResearch }) {
  const arxivId = source.arxiv_id || '';
  const title = source.title || source.source_file || 'Unknown';
  const arxivUrl = arxivId ? `https://arxiv.org/abs/${arxivId}` : null;
  const relevance = source.relevance_score;

  // For cosine distance, lower = more relevant. Normalize for display.
  const barWidth = relevance != null ? Math.max(10, Math.min(100, (1 - relevance) * 100)) : 0;

  return (
    <div className="source-card">
      <div className="source-title">
        {index}. {title}
      </div>
      <div className="source-meta">
        {isResearch && arxivUrl ? (
          <a href={arxivUrl} target="_blank" rel="noopener noreferrer" className="source-link">
            arXiv:{arxivId}
          </a>
        ) : null}
        <span>Page {source.page ?? 'N/A'}</span>
        {relevance != null && (
          <>
            <span>Relevance: {relevance.toFixed(3)}</span>
            <div className="relevance-bar">
              <div className="relevance-bar-fill" style={{ width: `${barWidth}%` }}></div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
