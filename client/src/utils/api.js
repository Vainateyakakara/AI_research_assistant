const BASE_URL = 'http://localhost:8000';

async function request(url, options = {}) {
  try {
    const response = await fetch(`${BASE_URL}${url}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    if (err.message.includes('Failed to fetch')) {
      throw new Error('Cannot connect to server. Is the backend running on port 8000?');
    }
    throw err;
  }
}

export async function postQuery(query, mode, showDetails = true, conversationId = null) {
  return request('/api/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      mode,
      show_details: showDetails,
      conversation_id: conversationId,
    }),
  });
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function getStatus() {
  return request('/api/status');
}

export async function getMemory() {
  return request('/api/memory');
}

export async function clearMemory() {
  return request('/api/memory', { method: 'DELETE' });
}

// ── Conversation API ─────────────────────────────────────────────────────────

export async function getConversations() {
  return request('/api/conversations');
}

export async function createConversation(title = 'New Chat') {
  return request('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function getConversationMessages(conversationId) {
  return request(`/api/conversations/${conversationId}/messages`);
}

export async function deleteConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`, { method: 'DELETE' });
}

export async function renameConversation(conversationId, title) {
  return request(`/api/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

export async function loadConversationIntoMemory(conversationId) {
  return request(`/api/memory/load/${conversationId}`, { method: 'POST' });
}
