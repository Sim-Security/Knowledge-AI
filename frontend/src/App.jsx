import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, MessageSquare, BookOpen, FolderTree, Settings,
  Plus, Send, Sparkles, FileText, Folder, Trash2, RefreshCw,
  ChevronRight, ChevronDown, X, Check, AlertCircle, Brain,
  GraduationCap, Tags, Link2, FileStack, Lightbulb, HelpCircle,
  BookMarked, Layers, Clock, Hash
} from 'lucide-react';
import { api, APIError } from './utils/api';

// ============================================================================
// Configuration Panel Component
// ============================================================================

function ConfigPanel({ isOpen, onClose, config, onConfigUpdate }) {
  const [formData, setFormData] = useState({
    openai_api_key: '',
    anthropic_api_key: '',
    embedding_provider: config?.embedding_provider || 'openai',
    chat_provider: config?.chat_provider || 'anthropic',
    ollama_base_url: config?.ollama_base_url || 'http://localhost:11434',
    ollama_model: config?.ollama_model || 'llama3.2',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.updateConfig(formData);
      onConfigUpdate();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-ink-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-white rounded-2xl shadow-floating max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-parchment-200">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold text-ink-900">Configuration</h2>
            <button onClick={onClose} className="btn-ghost p-2">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-2">
              OpenAI API Key
              {config?.has_openai_key && (
                <span className="ml-2 text-sage-600 text-xs">(configured)</span>
              )}
            </label>
            <input
              type="password"
              className="input-field"
              placeholder="sk-..."
              value={formData.openai_api_key}
              onChange={(e) => setFormData({ ...formData, openai_api_key: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-2">
              Anthropic API Key
              {config?.has_anthropic_key && (
                <span className="ml-2 text-sage-600 text-xs">(configured)</span>
              )}
            </label>
            <input
              type="password"
              className="input-field"
              placeholder="sk-ant-..."
              value={formData.anthropic_api_key}
              onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                Embedding Provider
              </label>
              <select
                className="input-field"
                value={formData.embedding_provider}
                onChange={(e) => setFormData({ ...formData, embedding_provider: e.target.value })}
              >
                <option value="openai">OpenAI</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-700 mb-2">
                Chat Provider
              </label>
              <select
                className="input-field"
                value={formData.chat_provider}
                onChange={(e) => setFormData({ ...formData, chat_provider: e.target.value })}
              >
                <option value="anthropic">Anthropic Claude</option>
                <option value="openai">OpenAI GPT-4</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
          </div>

          {(formData.embedding_provider === 'ollama' || formData.chat_provider === 'ollama') && (
            <div className="p-4 bg-parchment-100 rounded-lg space-y-4">
              <p className="text-sm text-ink-600">Ollama Settings (for local models)</p>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-2">
                  Ollama URL
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.ollama_base_url}
                  onChange={(e) => setFormData({ ...formData, ollama_base_url: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-2">
                  Model Name
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.ollama_model}
                  onChange={(e) => setFormData({ ...formData, ollama_model: e.target.value })}
                />
              </div>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-parchment-200 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ============================================================================
// Search Results Component
// ============================================================================

function SearchResults({ results, query }) {
  if (!results?.length) {
    return (
      <div className="text-center py-12 text-ink-500">
        <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No results found for "{query}"</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-500">{results.length} results for "{query}"</p>
      {results.map((result, index) => (
        <motion.div
          key={result.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          className="card p-4"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-ember-500" />
              <span className="font-medium text-ink-800">{result.metadata?.file_name}</span>
            </div>
            <span className="tag tag-sage">
              {Math.round(result.similarity * 100)}% match
            </span>
          </div>
          <p className="text-sm text-ink-600 line-clamp-3">{result.content}</p>
          <div className="mt-3 flex items-center gap-2 text-xs text-ink-400">
            <span>Chunk {result.metadata?.chunk_index + 1} of {result.metadata?.total_chunks}</span>
            <span>•</span>
            <span>{result.metadata?.file_type}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================================
// Chat Message Component
// ============================================================================

function ChatMessage({ message, isUser, sources }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[80%] ${isUser ? 'order-2' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-ember-500 text-white rounded-tr-md'
              : 'bg-white border border-parchment-200 shadow-paper rounded-tl-md'
          }`}
        >
          <div className={`prose-knowledge ${isUser ? 'text-white' : ''}`}>
            {message.split('\n').map((line, i) => (
              <p key={i} className="mb-2 last:mb-0">{line}</p>
            ))}
          </div>
        </div>
        
        {sources?.length > 0 && !isUser && (
          <div className="mt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-ink-500 hover:text-ink-700 flex items-center gap-1"
            >
              <FileStack className="w-3 h-3" />
              {sources.length} source{sources.length > 1 ? 's' : ''}
              {showSources ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            
            <AnimatePresence>
              {showSources && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 space-y-2">
                    {sources.map((source, i) => (
                      <div key={i} className="text-xs p-2 bg-parchment-100 rounded-lg">
                        <span className="font-medium text-ink-700">{source.source}</span>
                        <p className="text-ink-500 mt-1 line-clamp-2">{source.preview}</p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================================
// Main App Component
// ============================================================================

export default function App() {
  // State
  const [activeTab, setActiveTab] = useState('chat');
  const [config, setConfig] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [files, setFiles] = useState([]);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMode, setChatMode] = useState('chat');
  const [conversationId, setConversationId] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  
  // Tutor state
  const [tutorMode, setTutorMode] = useState('quiz');
  const [tutorTopic, setTutorTopic] = useState('');
  const [tutorResult, setTutorResult] = useState(null);
  const [tutorLoading, setTutorLoading] = useState(false);
  
  // Index state
  const [indexPath, setIndexPath] = useState('');
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState(null);
  const [filterPreset, setFilterPreset] = useState('auto');
  const [checkSensitive, setCheckSensitive] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState(null);
  
  // Refs
  const chatEndRef = useRef(null);
  const chatInputRef = useRef(null);

  // Load initial data
  useEffect(() => {
    loadConfig();
    loadStats();
    loadFiles();
  }, []);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConfig = async () => {
    try {
      const data = await api.getConfig();
      setConfig(data);
      if (!data.is_configured) {
        setConfigOpen(true);
      }
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  };

  const loadStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadFiles = async () => {
    try {
      const data = await api.getFiles();
      setFiles(data.files || []);
    } catch (err) {
      console.error('Failed to load files:', err);
    }
  };

  // Search handler
  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) return;
    
    setSearching(true);
    try {
      const results = await api.search(searchQuery);
      setSearchResults(results);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  // Chat handler
  const handleChat = async (e) => {
    e?.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    
    const userMessage = chatInput;
    setChatInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);
    
    try {
      const response = await api.chat(userMessage, {
        conversationId,
        mode: chatMode,
      });
      
      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.response, sources: response.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, error: true },
      ]);
    } finally {
      setChatLoading(false);
      chatInputRef.current?.focus();
    }
  };

  // Preview handler
  const handlePreview = async () => {
    if (!indexPath.trim()) return;
    
    setPreviewing(true);
    setPreviewResult(null);
    try {
      const result = await api.previewIndex(indexPath, {
        filterPreset,
        checkSensitiveContent: checkSensitive,
      });
      setPreviewResult(result);
    } catch (err) {
      setPreviewResult({ error: err.message });
    } finally {
      setPreviewing(false);
    }
  };

  // Index handler
  const handleIndex = async (e) => {
    e?.preventDefault();
    if (!indexPath.trim()) return;
    
    setIndexing(true);
    setIndexResult(null);
    setPreviewResult(null);
    try {
      const result = await api.indexPath(indexPath, {
        filterPreset,
        checkSensitiveContent: checkSensitive,
      });
      setIndexResult(result);
      loadStats();
      loadFiles();
    } catch (err) {
      setIndexResult({ error: err.message });
    } finally {
      setIndexing(false);
    }
  };

  // Tutor handler
  const handleTutor = async () => {
    setTutorLoading(true);
    setTutorResult(null);
    try {
      const result = await api.tutor({
        topic: tutorTopic || undefined,
        mode: tutorMode,
      });
      setTutorResult(result);
    } catch (err) {
      setTutorResult({ error: err.message });
    } finally {
      setTutorLoading(false);
    }
  };

  // Clear chat
  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
  };

  // Navigation items
  const navItems = [
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'search', icon: Search, label: 'Search' },
    { id: 'tutor', icon: GraduationCap, label: 'Tutor' },
    { id: 'files', icon: FolderTree, label: 'Files' },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-parchment-200 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-parchment-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ember-500 to-ember-600 flex items-center justify-center shadow-md">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-display font-semibold text-ink-900">Knowledge AI</h1>
              <p className="text-xs text-ink-500">Your Personal Assistant</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    activeTab === item.id
                      ? 'bg-ember-50 text-ember-700 font-medium'
                      : 'text-ink-600 hover:bg-parchment-100 hover:text-ink-800'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Stats */}
        <div className="p-4 border-t border-parchment-200">
          <div className="p-4 bg-parchment-50 rounded-xl">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-ink-700">Knowledge Base</span>
              <button onClick={loadStats} className="text-ink-400 hover:text-ink-600">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-2xl font-display font-bold text-ink-900">
                  {stats?.unique_files || 0}
                </p>
                <p className="text-xs text-ink-500">Files</p>
              </div>
              <div>
                <p className="text-2xl font-display font-bold text-ink-900">
                  {stats?.total_chunks || 0}
                </p>
                <p className="text-xs text-ink-500">Chunks</p>
              </div>
            </div>
          </div>
        </div>

        {/* Settings */}
        <div className="p-4 border-t border-parchment-200">
          <button
            onClick={() => setConfigOpen(true)}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-ink-600 hover:bg-parchment-100 hover:text-ink-800 transition-all"
          >
            <Settings className="w-5 h-5" />
            Settings
            {!config?.is_configured && (
              <span className="ml-auto w-2 h-2 rounded-full bg-ember-500"></span>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col">
            {/* Chat Header */}
            <header className="px-6 py-4 border-b border-parchment-200 bg-white/80 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-lg font-semibold text-ink-900">Chat with Your Knowledge</h2>
                  <p className="text-sm text-ink-500">Ask questions about your indexed documents</p>
                </div>
                <div className="flex items-center gap-3">
                  <select
                    value={chatMode}
                    onChange={(e) => setChatMode(e.target.value)}
                    className="input-field py-2 text-sm w-40"
                  >
                    <option value="chat">💬 Chat</option>
                    <option value="tutor">📚 Tutor Mode</option>
                    <option value="summarize">📝 Summarize</option>
                    <option value="organize">🗂️ Organize</option>
                  </select>
                  {messages.length > 0 && (
                    <button onClick={clearChat} className="btn-ghost text-sm">
                      <Trash2 className="w-4 h-4 mr-1" />
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </header>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center max-w-md">
                    <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-ember-100 to-sage-100 flex items-center justify-center">
                      <Sparkles className="w-8 h-8 text-ember-500" />
                    </div>
                    <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                      Start a Conversation
                    </h3>
                    <p className="text-ink-500 mb-6">
                      Ask questions about your indexed documents. I'll search through your knowledge base to provide relevant answers.
                    </p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {['What topics do I have notes on?', 'Summarize my recent documents', 'Help me understand...'].map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => setChatInput(suggestion)}
                          className="tag hover:bg-parchment-200 cursor-pointer transition-colors"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 max-w-3xl mx-auto">
                  {messages.map((msg, i) => (
                    <ChatMessage
                      key={i}
                      message={msg.content}
                      isUser={msg.role === 'user'}
                      sources={msg.sources}
                    />
                  ))}
                  {chatLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2 text-ink-500"
                    >
                      <div className="w-2 h-2 rounded-full bg-ember-500 animate-pulse-subtle"></div>
                      <span className="text-sm">Thinking...</span>
                    </motion.div>
                  )}
                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-parchment-200 bg-white">
              <form onSubmit={handleChat} className="max-w-3xl mx-auto">
                <div className="flex gap-3">
                  <input
                    ref={chatInputRef}
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask about your documents..."
                    className="input-field flex-1"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    className="btn-primary flex items-center gap-2"
                    disabled={chatLoading || !chatInput.trim()}
                  >
                    <Send className="w-4 h-4" />
                    Send
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="flex-1 flex flex-col">
            <header className="px-6 py-4 border-b border-parchment-200 bg-white/80 backdrop-blur-sm">
              <h2 className="font-display text-lg font-semibold text-ink-900">Semantic Search</h2>
              <p className="text-sm text-ink-500">Find relevant content by meaning, not just keywords</p>
            </header>

            <div className="p-6">
              <form onSubmit={handleSearch} className="max-w-2xl mb-6">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search your knowledge base..."
                    className="input-field flex-1"
                  />
                  <button
                    type="submit"
                    className="btn-primary flex items-center gap-2"
                    disabled={searching}
                  >
                    <Search className="w-4 h-4" />
                    {searching ? 'Searching...' : 'Search'}
                  </button>
                </div>
              </form>

              {searchResults && (
                <SearchResults results={searchResults.results} query={searchResults.query} />
              )}
            </div>
          </div>
        )}

        {/* Tutor Tab */}
        {activeTab === 'tutor' && (
          <div className="flex-1 flex flex-col">
            <header className="px-6 py-4 border-b border-parchment-200 bg-white/80 backdrop-blur-sm">
              <h2 className="font-display text-lg font-semibold text-ink-900">AI Tutor</h2>
              <p className="text-sm text-ink-500">Learn from your documents with quizzes, flashcards, and study guides</p>
            </header>

            <div className="p-6">
              <div className="max-w-2xl space-y-6">
                {/* Mode Selection */}
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { id: 'quiz', icon: HelpCircle, label: 'Quiz Me' },
                    { id: 'explain', icon: Lightbulb, label: 'Explain' },
                    { id: 'flashcards', icon: Layers, label: 'Flashcards' },
                    { id: 'study_guide', icon: BookMarked, label: 'Study Guide' },
                  ].map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => setTutorMode(mode.id)}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        tutorMode === mode.id
                          ? 'border-ember-500 bg-ember-50'
                          : 'border-parchment-200 hover:border-parchment-300'
                      }`}
                    >
                      <mode.icon className={`w-6 h-6 mx-auto mb-2 ${
                        tutorMode === mode.id ? 'text-ember-600' : 'text-ink-400'
                      }`} />
                      <span className={`text-sm font-medium ${
                        tutorMode === mode.id ? 'text-ember-700' : 'text-ink-600'
                      }`}>
                        {mode.label}
                      </span>
                    </button>
                  ))}
                </div>

                {/* Topic Input */}
                <div>
                  <label className="block text-sm font-medium text-ink-700 mb-2">
                    Topic (optional)
                  </label>
                  <input
                    type="text"
                    value={tutorTopic}
                    onChange={(e) => setTutorTopic(e.target.value)}
                    placeholder="Enter a topic to focus on..."
                    className="input-field"
                  />
                </div>

                <button
                  onClick={handleTutor}
                  disabled={tutorLoading}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  <GraduationCap className="w-5 h-5" />
                  {tutorLoading ? 'Generating...' : 'Generate Learning Content'}
                </button>

                {/* Results */}
                {tutorResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-6"
                  >
                    {tutorResult.error ? (
                      <div className="text-red-600">{tutorResult.error}</div>
                    ) : (
                      <div className="prose-knowledge">
                        {tutorResult.content?.split('\n').map((line, i) => (
                          <p key={i} className="mb-2">{line}</p>
                        ))}
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <div className="flex-1 flex flex-col">
            <header className="px-6 py-4 border-b border-parchment-200 bg-white/80 backdrop-blur-sm">
              <h2 className="font-display text-lg font-semibold text-ink-900">Knowledge Base</h2>
              <p className="text-sm text-ink-500">Manage your indexed files with smart filtering</p>
            </header>

            <div className="p-6 overflow-y-auto">
              {/* Index Form */}
              <div className="max-w-2xl mb-8">
                <label className="block text-sm font-medium text-ink-700 mb-2">
                  Add Files or Folders
                </label>
                <div className="flex gap-3 mb-4">
                  <input
                    type="text"
                    value={indexPath}
                    onChange={(e) => setIndexPath(e.target.value)}
                    placeholder="/path/to/your/documents or ~/Documents"
                    className="input-field flex-1 font-mono text-sm"
                  />
                </div>
                
                {/* Filter Settings */}
                <div className="p-4 bg-parchment-50 rounded-xl mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Settings className="w-4 h-4 text-ink-500" />
                    <span className="text-sm font-medium text-ink-700">Smart Filter Settings</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-ink-600 mb-1">Filter Preset</label>
                      <select
                        value={filterPreset}
                        onChange={(e) => setFilterPreset(e.target.value)}
                        className="input-field py-2 text-sm"
                      >
                        <option value="auto">🔮 Auto-detect</option>
                        <option value="code">💻 Code Project</option>
                        <option value="notes">📝 Notes & Documents</option>
                        <option value="research">🔬 Research & PDFs</option>
                        <option value="none">⚠️ No Filter (dangerous)</option>
                      </select>
                    </div>
                    
                    <div className="flex items-end">
                      <label className="flex items-center gap-2 text-sm text-ink-600">
                        <input
                          type="checkbox"
                          checked={checkSensitive}
                          onChange={(e) => setCheckSensitive(e.target.checked)}
                          className="rounded border-parchment-300"
                        />
                        Block sensitive files (.env, credentials, etc.)
                      </label>
                    </div>
                  </div>
                  
                  <div className="mt-3 text-xs text-ink-500">
                    {filterPreset === 'auto' && '✨ Automatically detects project type (package.json, pyproject.toml, etc.)'}
                    {filterPreset === 'code' && '🚫 Ignores: node_modules, venv, .git, dist, build, lock files, minified code'}
                    {filterPreset === 'notes' && '📄 Optimized for documents, allows larger files'}
                    {filterPreset === 'research' && '📚 Includes PDFs, supports files up to 100MB'}
                    {filterPreset === 'none' && '⚠️ Warning: Will index everything including sensitive files!'}
                  </div>
                </div>
                
                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={handlePreview}
                    className="btn-secondary flex items-center gap-2"
                    disabled={!indexPath.trim() || previewing}
                  >
                    <Search className="w-4 h-4" />
                    {previewing ? 'Scanning...' : 'Preview'}
                  </button>
                  <button
                    onClick={handleIndex}
                    className="btn-primary flex items-center gap-2"
                    disabled={indexing || !indexPath.trim()}
                  >
                    <Plus className="w-4 h-4" />
                    {indexing ? 'Indexing...' : 'Index Files'}
                  </button>
                </div>
              </div>

              {/* Preview Results */}
              {previewResult && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 p-4 bg-white rounded-xl border border-parchment-200 max-w-2xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-ink-800">Index Preview</h3>
                    <button 
                      onClick={() => setPreviewResult(null)}
                      className="text-ink-400 hover:text-ink-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="text-center p-3 bg-parchment-50 rounded-lg">
                      <p className="text-2xl font-display font-bold text-ink-900">{previewResult.total_files}</p>
                      <p className="text-xs text-ink-500">Total Files</p>
                    </div>
                    <div className="text-center p-3 bg-sage-50 rounded-lg">
                      <p className="text-2xl font-display font-bold text-sage-700">{previewResult.will_index}</p>
                      <p className="text-xs text-sage-600">Will Index</p>
                    </div>
                    <div className="text-center p-3 bg-ink-50 rounded-lg">
                      <p className="text-2xl font-display font-bold text-ink-600">{previewResult.will_skip}</p>
                      <p className="text-xs text-ink-500">Will Skip</p>
                    </div>
                  </div>
                  
                  {/* Skip Summary */}
                  {previewResult.skip_summary && Object.keys(previewResult.skip_summary).length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm font-medium text-ink-700 mb-2">Skipped Files by Reason:</p>
                      <div className="space-y-2">
                        {Object.entries(previewResult.skip_summary).map(([category, info]) => (
                          <div key={category} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <span className={`tag ${category === 'sensitive' ? 'tag-ember' : ''}`}>
                                {category}
                              </span>
                              <span className="text-ink-500 text-xs">
                                {info.examples?.slice(0, 3).join(', ')}
                                {info.examples?.length > 3 && '...'}
                              </span>
                            </div>
                            <span className="font-medium text-ink-700">{info.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Sample files to index */}
                  {previewResult.index_preview?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-ink-700 mb-2">
                        Sample files to index ({Math.min(10, previewResult.index_preview.length)} of {previewResult.will_index}):
                      </p>
                      <div className="max-h-32 overflow-y-auto space-y-1">
                        {previewResult.index_preview.slice(0, 10).map((file, i) => (
                          <div key={i} className="text-xs text-ink-600 font-mono truncate">
                            {file.name}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Index Result */}
              {indexResult && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mb-6 p-4 rounded-lg max-w-2xl ${
                    indexResult.error
                      ? 'bg-red-50 border border-red-200'
                      : 'bg-sage-50 border border-sage-200'
                  }`}
                >
                  {indexResult.error ? (
                    <div className="flex items-center gap-2 text-red-700">
                      <AlertCircle className="w-5 h-5" />
                      <span>{indexResult.error}</span>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 text-sage-700 mb-2">
                        <Check className="w-5 h-5" />
                        <span className="font-medium">
                          Indexed {indexResult.indexed} files
                          {indexResult.skipped > 0 && `, skipped ${indexResult.skipped}`}
                          {indexResult.errors > 0 && `, ${indexResult.errors} errors`}
                        </span>
                      </div>
                      
                      {indexResult.sensitive_files_blocked > 0 && (
                        <div className="flex items-center gap-2 text-amber-600 text-sm mt-2">
                          <AlertCircle className="w-4 h-4" />
                          <span>
                            {indexResult.sensitive_files_blocked} sensitive file(s) blocked for security
                          </span>
                        </div>
                      )}
                      
                      {indexResult.filter_stats && (
                        <div className="mt-3 pt-3 border-t border-sage-200 text-sm text-sage-600">
                          <p className="font-medium mb-1">Filter Statistics:</p>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                            <span>Scanned: {indexResult.filter_stats.total_scanned}</span>
                            <span>By pattern: {indexResult.filter_stats.ignored?.by_pattern || 0}</span>
                            <span>Sensitive: {indexResult.filter_stats.ignored?.sensitive || 0}</span>
                            <span>Size limits: {indexResult.filter_stats.ignored?.size || 0}</span>
                            <span>Low quality: {indexResult.filter_stats.ignored?.quality || 0}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              )}

              {/* File List */}
              <div className="max-w-4xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-ink-800">Indexed Files ({files.length})</h3>
                  {files.length > 0 && (
                    <button
                      onClick={async () => {
                        if (confirm('Clear all indexed files?')) {
                          await api.clearIndex();
                          loadStats();
                          loadFiles();
                        }
                      }}
                      className="btn-ghost text-sm text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Clear All
                    </button>
                  )}
                </div>

                {files.length === 0 ? (
                  <div className="text-center py-12 text-ink-500">
                    <Folder className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No files indexed yet</p>
                    <p className="text-sm">Add a folder path above to get started</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {files.map((file, i) => (
                      <motion.div
                        key={file.path}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.02 }}
                        className="flex items-center gap-3 p-3 bg-white rounded-lg border border-parchment-200"
                      >
                        <FileText className="w-5 h-5 text-ink-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-ink-800 truncate">{file.name}</p>
                          <p className="text-xs text-ink-400 truncate">{file.path}</p>
                        </div>
                        <span className="tag">{file.chunks} chunks</span>
                        <span className="tag tag-sage">{file.type}</span>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Config Modal */}
      <AnimatePresence>
        <ConfigPanel
          isOpen={configOpen}
          onClose={() => setConfigOpen(false)}
          config={config}
          onConfigUpdate={loadConfig}
        />
      </AnimatePresence>
    </div>
  );
}
