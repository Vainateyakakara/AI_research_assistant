import { useState } from 'react';
import PipelineBadge from './PipelineBadge';
import SourceCard from './SourceCard';

/* ── Simple markdown renderer ─────────────────────────────────────────────── */
function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeBuffer = [];
  let listBuffer = [];
  let listType = null;

  function flushList() {
    if (listBuffer.length > 0) {
      const Tag = listType === 'ol' ? 'ol' : 'ul';
      elements.push(
        <Tag key={`list-${elements.length}`}>
          {listBuffer.map((item, i) => <li key={i}>{processInline(item)}</li>)}
        </Tag>
      );
      listBuffer = [];
      listType = null;
    }
  }

  function processInline(text) {
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    return <span dangerouslySetInnerHTML={{ __html: text }} />;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`}><code>{codeBuffer.join('\n')}</code></pre>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      flushList();
      continue;
    }

    // Headers
    const h3Match = line.match(/^### (.+)/);
    if (h3Match) { flushList(); elements.push(<h3 key={i}>{processInline(h3Match[1])}</h3>); continue; }

    const h2Match = line.match(/^## (.+)/);
    if (h2Match) { flushList(); elements.push(<h2 key={i}>{processInline(h2Match[1])}</h2>); continue; }

    const h1Match = line.match(/^# (.+)/);
    if (h1Match) { flushList(); elements.push(<h1 key={i}>{processInline(h1Match[1])}</h1>); continue; }

    // Unordered list
    const ulMatch = line.match(/^[\s]*[-*•]\s+(.+)/);
    if (ulMatch) {
      if (listType === 'ol') flushList();
      listType = 'ul';
      listBuffer.push(ulMatch[1]);
      continue;
    }

    // Ordered list
    const olMatch = line.match(/^[\s]*\d+\.\s+(.+)/);
    if (olMatch) {
      if (listType === 'ul') flushList();
      listType = 'ol';
      listBuffer.push(olMatch[1]);
      continue;
    }

    // Paragraph
    flushList();
    elements.push(<p key={i}>{processInline(line)}</p>);
  }

  flushList();
  return elements;
}


export default function MessageBubble({ entry, showDetails }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [extractedOpen, setExtractedOpen] = useState(false);
  const { query, rewritten, resolvedPaper, result, mode } = entry;
  const isResearch = result.type === 'research';

  // Deduplicate sources for research mode
  let displaySources = result.sources || [];
  if (isResearch && displaySources.length > 0) {
    const seen = new Set();
    displaySources = displaySources.filter(s => {
      const id = s.arxiv_id || s.source_file;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  }

  const totalChunks = result.sources?.length || 0;
  const uniqueCount = displaySources.length;

  return (
    <div className="message-turn">
      {/* User bubble */}
      <div className="message-label user-label">You</div>
      <div className="message-bubble user">{query}</div>

      {/* Annotation pills */}
      {(rewritten || resolvedPaper) && (
        <div className="annotation-pills">
          {resolvedPaper && (
            <span className="annotation-pill reference">
              📎 Resolved → {resolvedPaper.substring(0, 60)}{resolvedPaper.length > 60 ? '…' : ''}
            </span>
          )}
          {rewritten && !resolvedPaper && (
            <span className="annotation-pill rewrite">
              ✏️ Interpreted as → {rewritten}
            </span>
          )}
        </div>
      )}

      {/* Assistant bubble */}
      <div className="message-label">🔬 Assistant</div>
      <div className="message-bubble assistant">
        <PipelineBadge type={result.type} model={result.model} />

        {/* Pipeline steps */}
        {showDetails && result.pipeline?.length > 0 && (
          <div className="pipeline-steps">
            {result.pipeline.map((step, i) => (
              <span key={i}>
                {i > 0 && <span className="pipeline-arrow"> → </span>}
                <span className="pipeline-step">{step}</span>
              </span>
            ))}
          </div>
        )}

        {/* Answer */}
        <div className="answer-content">
          {renderMarkdown(result.answer)}
        </div>

        {/* Sources */}
        {displaySources.length > 0 && (
          <div className="sources-section">
            <button className="sources-toggle" onClick={() => setSourcesOpen(!sourcesOpen)}>
              {isResearch
                ? `📚 arXiv Sources — ${uniqueCount} paper(s), ${totalChunks} chunks`
                : `📄 Local Sources (${totalChunks} chunks)`
              }
              <span className={`sources-toggle-icon ${sourcesOpen ? 'open' : ''}`}>▼</span>
            </button>
            {sourcesOpen && (
              <div className="sources-list">
                {displaySources.map((source, i) => (
                  <SourceCard key={i} source={source} index={i + 1} isResearch={isResearch} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Extracted info */}
        {result.extracted_info && showDetails && (
          <div className="sources-section">
            <button className="sources-toggle" onClick={() => setExtractedOpen(!extractedOpen)}>
              🧪 Extracted Information (pre-synthesis)
              <span className={`sources-toggle-icon ${extractedOpen ? 'open' : ''}`}>▼</span>
            </button>
            {extractedOpen && (
              <div className="answer-content" style={{ marginTop: '8px' }}>
                {renderMarkdown(result.extracted_info)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
