import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import QueryInput from './components/QueryInput';
import UploadPanel from './components/UploadPanel';
import { useChat } from './hooks/useChat';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [showDetails, setShowDetails] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [loadingMode, setLoadingMode] = useState(null);

  const {
    messages,
    isLoading,
    error,
    conversationId,
    sendQuery,
    clearHistory,
    loadConversation,
    startNewChat,
  } = useChat();

  async function handleSubmit(query, mode) {
    setLoadingMode(mode);
    await sendQuery(query, mode);
    setRefreshTrigger(prev => prev + 1);
    setLoadingMode(null);
  }

  function handleExampleClick(query) {
    const textarea = document.getElementById('query-input');
    if (textarea) {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      ).set;
      nativeSetter.call(textarea, query);
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  function handleClearMemory() {
    clearHistory();
    setRefreshTrigger(prev => prev + 1);
  }

  function handleUploadComplete() {
    setRefreshTrigger(prev => prev + 1);
  }

  function handleNewChat() {
    startNewChat();
    setRefreshTrigger(prev => prev + 1);
  }

  async function handleSelectConversation(convId) {
    if (convId === conversationId) return;
    await loadConversation(convId);
    setRefreshTrigger(prev => prev + 1);
    setActiveTab('chat');
  }

  return (
    <div className="app-layout">
      <Sidebar
        refreshTrigger={refreshTrigger}
        onClearMemory={handleClearMemory}
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
      />

      <div className="main-content">
        {/* Tab navigation */}
        <div className="tab-nav">
          <button
            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
            id="tab-chat"
          >
            💬 Ask Questions
          </button>
          <button
            className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
            id="tab-upload"
          >
            📤 Upload Papers
          </button>
        </div>

        {/* Tab content */}
        {activeTab === 'chat' ? (
          <div className="chat-page">
            <ChatPanel
              messages={messages}
              isLoading={isLoading}
              loadingMode={loadingMode}
              showDetails={showDetails}
              onExampleClick={handleExampleClick}
            />

            {error && (
              <div style={{
                padding: '8px 24px',
                background: 'var(--error-bg)',
                color: 'var(--error)',
                fontSize: '0.82rem',
                textAlign: 'center',
              }}>
                ⚠️ {error}
              </div>
            )}

            <QueryInput
              onSubmit={handleSubmit}
              isLoading={isLoading}
              showDetails={showDetails}
              onToggleDetails={setShowDetails}
            />
          </div>
        ) : (
          <UploadPanel onUploadComplete={handleUploadComplete} />
        )}
      </div>
    </div>
  );
}
