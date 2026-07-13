export default function PipelineBadge({ type, model }) {
  const badgeClass = {
    simple: 'simple',
    analytical: 'analytical',
    research: 'research',
  }[type] || 'simple';

  return (
    <div className="assistant-header">
      <span className={`mode-badge ${badgeClass}`}>{type?.toUpperCase()}</span>
      {model && <span className="model-label">Model: {model}</span>}
    </div>
  );
}
