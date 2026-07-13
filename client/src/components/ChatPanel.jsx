import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import LoadingSpinner from './LoadingSpinner';

export default function ChatPanel({ messages, isLoading, loadingMode, showDetails, onExampleClick }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="chat-container">
        <div className="empty-state">
          <div className="empty-state-icon">🔬</div>
          <div className="empty-state-title">Ask a Research Question</div>
          <div className="empty-state-subtitle">
            Upload papers and analyse them, search arXiv for the latest research,
            or get quick answers to any question.
          </div>
          <div className="example-queries">
            {[
              'What is a transformer?',
              'Compare BERT and GPT architectures',
              'Latest research on RAG systems',
              'Explain multimodal learning advancements',
            ].map((q, i) => (
              <button key={i} className="example-query" onClick={() => onExampleClick?.(q)}>
                💡 {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {messages.map((entry) => (
        <MessageBubble key={entry.id} entry={entry} showDetails={showDetails} />
      ))}
      {isLoading && <LoadingSpinner mode={loadingMode} />}
      <div ref={bottomRef} />
    </div>
  );
}
