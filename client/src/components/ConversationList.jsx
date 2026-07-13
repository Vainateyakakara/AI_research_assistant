import { useState, useEffect } from 'react';
import { getConversations, deleteConversation } from '../utils/api';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ConversationList({
  activeConversationId,
  onSelectConversation,
  onNewChat,
  refreshTrigger,
}) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConversations();
  }, [refreshTrigger]);

  async function fetchConversations() {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch {
      // Backend not running
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(e, convId) {
    e.stopPropagation();
    try {
      await deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (convId === activeConversationId) {
        onNewChat();
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="conversation-list">
      <button className="btn-new-chat" onClick={onNewChat} id="btn-new-chat">
        <span className="btn-new-chat-icon">✨</span>
        New Chat
      </button>

      {loading ? (
        <div className="conv-loading">Loading...</div>
      ) : conversations.length === 0 ? (
        <div className="conv-empty">No conversations yet</div>
      ) : (
        <div className="conv-items">
          {conversations.map(conv => (
            <div
              key={conv.id}
              className={`conv-item ${conv.id === activeConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
              id={`conv-${conv.id}`}
            >
              <div className="conv-item-content">
                <div className="conv-item-title">
                  {conv.title || 'New Chat'}
                </div>
                <div className="conv-item-meta">
                  {timeAgo(conv.updatedAt)}
                  {conv.messageCount > 0 && (
                    <span className="conv-item-count">
                      {Math.ceil(conv.messageCount / 2)} msg{Math.ceil(conv.messageCount / 2) !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>
              <button
                className="conv-item-delete"
                onClick={(e) => handleDelete(e, conv.id)}
                title="Delete conversation"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
