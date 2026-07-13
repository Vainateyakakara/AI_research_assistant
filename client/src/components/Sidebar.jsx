import { useState, useEffect } from 'react';
import { getStatus, getMemory, clearMemory } from '../utils/api';
import ConversationList from './ConversationList';

export default function Sidebar({
  refreshTrigger,
  onClearMemory,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}) {
  const [status, setStatus] = useState(null);
  const [memory, setMemory] = useState(null);
  const [statsExpanded, setStatsExpanded] = useState(false);

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  async function fetchData() {
    try {
      const [s, m] = await Promise.all([getStatus(), getMemory()]);
      setStatus(s);
      setMemory(m);
    } catch {
      // Backend not running yet
    }
  }

  async function handleClearMemory() {
    try {
      await clearMemory();
      setMemory(null);
      if (onClearMemory) onClearMemory();
      fetchData();
    } catch {
      // ignore
    }
  }

  return (
    <aside className="sidebar" id="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-title">
          <span className="sidebar-title-icon">🔬</span>
          AI Research Assistant
        </div>
        <div className="sidebar-caption">
          Powered by Groq + Gemini
        </div>
      </div>

      {/* Conversation History */}
      <div className="sidebar-section sidebar-section-conversations">
        <div className="sidebar-section-title">Conversations</div>
        <ConversationList
          activeConversationId={activeConversationId}
          onSelectConversation={onSelectConversation}
          onNewChat={onNewChat}
          refreshTrigger={refreshTrigger}
        />
      </div>

      {/* Collapsible System Stats */}
      <div className="sidebar-section">
        <button
          className="sources-toggle"
          onClick={() => setStatsExpanded(!statsExpanded)}
        >
          System & Stats
          <span className={`sources-toggle-icon ${statsExpanded ? 'open' : ''}`}>▼</span>
        </button>

        {statsExpanded && (
          <div className="sidebar-stats-content">
            {/* System Status */}
            <div className="sidebar-subsection">
              <div className="status-row">
                <span className={`status-dot ${status?.groqConfigured ? 'active' : 'inactive'}`}></span>
                Groq: {status?.groqConfigured ? 'Connected' : 'N/A'}
              </div>
              <div className="status-row">
                <span className={`status-dot ${status?.geminiConfigured ? 'active' : 'inactive'}`}></span>
                Gemini: {status?.geminiConfigured ? 'Connected' : 'N/A'}
              </div>
            </div>

            {/* Knowledge Base */}
            <div className="sidebar-subsection">
              <div className="sidebar-metric">
                <span className="sidebar-metric-value">{status?.numDocuments ?? '—'}</span>
                <span className="sidebar-metric-label">chunks in DB</span>
              </div>
            </div>

            {/* Session Memory */}
            <div className="sidebar-subsection">
              <div className="sidebar-metric">
                <span className="sidebar-metric-value">{memory?.turnsCount ?? 0}</span>
                <span className="sidebar-metric-label">turns in cache</span>
              </div>
              {memory?.lastTopic && (
                <div className="sidebar-info">
                  Topic: <strong>{memory.lastTopic}</strong>
                </div>
              )}
              <button className="btn-clear" onClick={handleClearMemory} style={{ marginTop: '8px' }}>
                🗑️ Clear Cache
              </button>
            </div>

            {/* Uploaded Papers */}
            <div className="sidebar-subsection">
              <div className="sidebar-section-title" style={{ fontSize: '0.72rem', marginBottom: '6px' }}>Uploaded Papers</div>
              {status?.uploadedPapers?.length > 0 ? (
                <ul className="paper-list">
                  {status.uploadedPapers.map((f, i) => (
                    <li key={i} className="paper-list-item">{f}</li>
                  ))}
                </ul>
              ) : (
                <div className="sidebar-info">No papers uploaded yet</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Query Modes */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Query Modes</div>
        <div className="mode-description">
          <span className="mode-badge analytical">ANALYSE</span>
          <div className="mode-description-text">
            Retrieval from local DB → Gemini
          </div>
        </div>
        <div className="mode-description">
          <span className="mode-badge research">RESEARCH</span>
          <div className="mode-description-text">
            arXiv → Download → Chunk → LLM
          </div>
        </div>
        <div className="mode-description">
          <span className="mode-badge simple">SIMPLE</span>
          <div className="mode-description-text">
            Direct Groq answer
          </div>
        </div>
      </div>
    </aside>
  );
}
