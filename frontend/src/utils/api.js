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
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };
  
  if (config.body && typeof config.body === 'object') {
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
  
  getStats: () => request('/stats'),
  getFiles: () => request('/files'),
  removeFile: (fileHash) => request(`/files/${fileHash}`, { method: 'DELETE' }),
  clearIndex: () => request('/index', { method: 'DELETE' }),
  
  // Search
  search: (query, options = {}) => request('/search', {
    method: 'POST',
    body: {
      query,
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
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),
};

export { APIError };
