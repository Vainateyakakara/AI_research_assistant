import { useState, useCallback } from 'react';
import {
  postQuery,
  clearMemory as clearMemoryAPI,
  getConversationMessages,
  loadConversationIntoMemory,
} from '../utils/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  const sendQuery = useCallback(async (query, mode) => {
    if (!query.trim() || isLoading) return null;

    setIsLoading(true);
    setError(null);

    try {
      const result = await postQuery(query, mode, true, conversationId);

      // If this was the first message, capture the conversation_id from server
      if (!conversationId && result.conversation_id) {
        setConversationId(result.conversation_id);
      }

      const entry = {
        id: Date.now(),
        query,
        rewritten: result.rewritten_query,
        resolvedPaper: result.resolved_paper,
        result,
        mode,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, entry]);
      return result.conversation_id || conversationId;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, conversationId]);

  const loadConversation = useCallback(async (convId) => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch messages from DB
      const data = await getConversationMessages(convId);
      // Load into server-side SessionMemory cache
      await loadConversationIntoMemory(convId);

      // Convert DB messages into the UI format (pair user+assistant)
      const entries = [];
      const msgs = data.messages || [];

      for (let i = 0; i < msgs.length; i++) {
        const msg = msgs[i];
        if (msg.role === 'user') {
          // Find the next assistant message
          const assistantMsg = msgs[i + 1]?.role === 'assistant' ? msgs[i + 1] : null;

          let sources = [];
          let pipeline = [];
          try { sources = assistantMsg?.sources ? JSON.parse(assistantMsg.sources) : []; } catch {}
          try { pipeline = assistantMsg?.pipeline ? JSON.parse(assistantMsg.pipeline) : []; } catch {}

          entries.push({
            id: Date.now() + i,
            query: msg.content,
            rewritten: assistantMsg?.rewrittenQuery || null,
            resolvedPaper: assistantMsg?.resolvedPaper || null,
            result: assistantMsg ? {
              answer: assistantMsg.content,
              type: assistantMsg.mode || 'simple',
              model: assistantMsg.modelUsed || '',
              sources,
              pipeline,
            } : null,
            mode: msg.mode || 'simple',
            timestamp: msg.createdAt || new Date().toISOString(),
          });

          if (assistantMsg) i++; // Skip the assistant message
        }
      }

      setMessages(entries);
      setConversationId(convId);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const startNewChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  const clearHistory = useCallback(async () => {
    try {
      await clearMemoryAPI();
      setMessages([]);
      setConversationId(null);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendQuery,
    clearHistory,
    loadConversation,
    startNewChat,
  };
}
