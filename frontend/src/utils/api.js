/**
 * API utility for communicating with the Knowledge AI backend
 */

const API_BASE = '/api';

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const config = {
    ...options,
    headers,
  };

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new APIError(
        data.detail || 'An error occurred',
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(error.message || 'Network error', 0, null);
  }
}

export const api = {
  // Health check
  health: () => request('/'),

  // Configuration
  getConfig: () => request('/config'),
  updateConfig: (config) => request('/config', {
    method: 'POST',
    body: config,
  }),

  // Indexing
  indexPath: (path, options = {}) => request('/index', {
    method: 'POST',
    body: {
      path,
      knowledge_base_id: options.knowledgeBaseId,
      recursive: options.recursive !== false,
      watch: options.watch || false,
      filter_preset: options.filterPreset || 'auto',
      extra_ignore_patterns: options.extraIgnorePatterns,
      extra_include_patterns: options.extraIncludePatterns,
      check_sensitive_content: options.checkSensitiveContent !== false,
      min_file_size: options.minFileSize || 50,
      max_file_size: options.maxFileSize || 10485760,
    },
  }),

  previewIndex: (path, options = {}) => request('/index/preview', {
    method: 'POST',
    body: {
      path,
      recursive: options.recursive !== false,
      filter_preset: options.filterPreset || 'auto',
      extra_ignore_patterns: options.extraIgnorePatterns,
      check_sensitive_content: options.checkSensitiveContent !== false,
    },
  }),

  getFilterConfig: () => request('/filter/config'),

  // Directory browsing
  browseDirectory: (path = null) => request('/browse', {
    method: 'POST',
    body: { path },
  }),

  getStats: (knowledgeBaseId) => request(`/stats${knowledgeBaseId ? `?knowledge_base_id=${knowledgeBaseId}` : ''}`),
  getFiles: (knowledgeBaseId) => request(`/files${knowledgeBaseId ? `?knowledge_base_id=${knowledgeBaseId}` : ''}`),
  removeFile: (fileHash, knowledgeBaseId, filePath) => {
    const params = new URLSearchParams();
    if (knowledgeBaseId) params.append('knowledge_base_id', knowledgeBaseId);
    if (filePath) params.append('file_path', filePath);
    return request(`/files/${fileHash || 'unknown'}?${params.toString()}`, { method: 'DELETE' });
  },
  uploadFile: (file, knowledgeBaseId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (knowledgeBaseId) formData.append('knowledge_base_id', knowledgeBaseId);

    // We need to bypass the default JSON handling in request() for FormData
    // But since request() handles headers and stringify automatically, we might need a slight adjustment or use fetch directly inside request logic if it supported it.
    // However, the existing request() helper forces 'Content-Type': 'application/json' in headers if not overridden, but FormData needs browser to set it.
    // Let's check request() implementation again.
    // Line 20: 'Content-Type': 'application/json', ...options.headers
    // We can override Content-Type to undefined to let browser handle it.

    return request('/upload', {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': undefined, // Let browser set boundary
      },
    });
  },
  clearIndex: (knowledgeBaseId) => request(`/index${knowledgeBaseId ? `?knowledge_base_id=${knowledgeBaseId}` : ''}`, { method: 'DELETE' }),

  // Search
  search: (query, options = {}) => request('/search', {
    method: 'POST',
    body: {
      query,
      knowledge_base_id: options.knowledgeBaseId,
      search_all: options.searchAll || false,
      top_k: options.topK || 10,
      file_types: options.fileTypes,
      folder_filter: options.folderFilter,
    },
  }),

  // Chat
  chat: (message, options = {}) => request('/chat', {
    method: 'POST',
    body: {
      message,
      knowledge_base_id: options.knowledgeBaseId,
      search_all: options.searchAll || false,
      conversation_id: options.conversationId,
      mode: options.mode || 'chat',
      include_sources: options.includeSources !== false,
      top_k: options.topK || 5,
    },
  }),

  // Tutor
  tutor: (options = {}) => request('/tutor', {
    method: 'POST',
    body: {
      topic: options.topic,
      document_ids: options.documentIds,
      mode: options.mode || 'quiz',
    },
  }),

  // Organize
  organize: (options = {}) => request('/organize', {
    method: 'POST',
    body: {
      document_ids: options.documentIds,
      action: options.action || 'suggest_tags',
    },
  }),

  // Conversations
  getConversations: () => request('/conversations'),
  getConversation: (id) => request(`/conversations/${id}`),
  createConversation: () => request('/conversations', { method: 'POST' }),
  renameConversation: (id, title) => request(`/conversations/${id}`, {
    method: 'PATCH',
    body: { title },
  }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),

  // Model discovery
  getOpenRouterModels: () => request('/models/openrouter'),
  getOllamaModels: () => request('/models/ollama'),

  // System / Local Mode
  getSystemHardware: () => request('/system/hardware'),
  getModelRecommendations: () => request('/system/recommendations'),
  getOllamaStatus: () => request('/system/ollama/status'),
  getInstalledOllamaModels: () => request('/system/ollama/models'),
  pullOllamaModel: (modelName) => request('/system/ollama/pull', {
    method: 'POST',
    body: { model_name: modelName },
  }),
  getLocalSetup: () => request('/system/local-setup'),

  // Embedding status and compatibility
  getEmbeddingStatus: () => request('/embedding/status'),

  // Knowledge Bases
  getKnowledgeBases: () => request('/knowledge-bases'),
  getKnowledgeBase: (id) => request(`/knowledge-bases/${id}`),
  createKnowledgeBase: (name, description) => request('/knowledge-bases', {
    method: 'POST',
    body: { name, description },
  }),
  updateKnowledgeBase: (id, updates) => request(`/knowledge-bases/${id}`, {
    method: 'PATCH',
    body: updates,
  }),
  deleteKnowledgeBase: (id) => request(`/knowledge-bases/${id}`, { method: 'DELETE' }),
};

export { APIError };
