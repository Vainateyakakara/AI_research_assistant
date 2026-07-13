import { useState, useRef } from 'react';

export default function QueryInput({ onSubmit, isLoading, showDetails, onToggleDetails }) {
  const [query, setQuery] = useState('');
  const [activeMode, setActiveMode] = useState(null);
  const textareaRef = useRef(null);

  function handleSubmit(mode) {
    if (!query.trim() || isLoading) return;
    setActiveMode(mode);
    onSubmit(query.trim(), mode);
    setQuery('');
  }

  function handleKeyDown(e) {
    // Ctrl+Enter to submit with last used mode or simple
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit('simple');
    }
  }

  // Expose a way for parent to set query (for example queries)
  QueryInput.setQuery = setQuery;

  return (
    <div className="query-input-area">
      <textarea
        ref={textareaRef}
        className="query-textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. 'Compare the two uploaded papers on attention'  •  'Latest research on RAG systems'  •  'What is a transformer?'"
        disabled={isLoading}
        id="query-input"
      />
      <div className="query-controls">
        <label className="details-toggle">
          <input
            type="checkbox"
            checked={showDetails}
            onChange={(e) => onToggleDetails(e.target.checked)}
            id="show-details-toggle"
          />
          Show pipeline details
        </label>
        <div className="mode-btn-group">
          <button
            className="mode-btn analysis"
            onClick={() => handleSubmit('analysis')}
            disabled={isLoading || !query.trim()}
            id="btn-analysis"
            title="Compare & analyse your uploaded PDFs — Retrieval from local DB + Gemini"
          >
            {isLoading && activeMode === 'analysis' ? (
              <span className="btn-spinner"></span>
            ) : '📊'}
            Analyse
          </button>
          <button
            className="mode-btn research"
            onClick={() => handleSubmit('research')}
            disabled={isLoading || !query.trim()}
            id="btn-research"
            title="Full arXiv pipeline: Search → Download → Chunk → Retrieve → LLM"
          >
            {isLoading && activeMode === 'research' ? (
              <span className="btn-spinner"></span>
            ) : '🔬'}
            Research
          </button>
          <button
            className="mode-btn simple"
            onClick={() => handleSubmit('simple')}
            disabled={isLoading || !query.trim()}
            id="btn-simple"
            title="Direct Groq answer — fast, no document retrieval"
          >
            {isLoading && activeMode === 'simple' ? (
              <span className="btn-spinner"></span>
            ) : '⚡'}
            Quick Answer
          </button>
        </div>
      </div>
    </div>
  );
}
