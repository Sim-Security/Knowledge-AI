import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  Search, MessageSquare, BookOpen, FolderTree, Settings,
  Plus, Send, Sparkles, FileText, Upload, Folder, Trash2, RefreshCw,
  ChevronRight, ChevronDown, X, Check, AlertCircle, Brain,
  GraduationCap, Tags, Link2, FileStack, Lightbulb, HelpCircle,
  BookMarked, Layers, Clock, Hash, Cpu, Download, Monitor, Zap, HardDrive, Wifi, WifiOff,
  Database, Edit3
} from 'lucide-react';
import { api, APIError } from './utils/api';

// ============================================================================
// Configuration Panel Component
// ============================================================================

function ConfigPanel({ isOpen, onClose, config, onConfigUpdate }) {
  const [formData, setFormData] = useState({
    openai_api_key: '',
    anthropic_api_key: '',
    openrouter_api_key: '',
    embedding_provider: config?.embedding_provider || 'openrouter',
    chat_provider: config?.chat_provider || 'openrouter',
    ollama_base_url: config?.ollama_base_url || 'http://localhost:11434',
    ollama_model: config?.ollama_model || 'llama3.2',
    ollama_embedding_model: config?.ollama_embedding_model || 'nomic-embed-text',
    openrouter_chat_model: config?.openrouter_chat_model || 'anthropic/claude-sonnet-4',
    openrouter_embedding_model: config?.openrouter_embedding_model || 'openai/text-embedding-3-small',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [availableModels, setAvailableModels] = useState({ chat: [], embedding: [] });
  const [loadingModels, setLoadingModels] = useState(false);

  // Local mode state
  const [localSetup, setLocalSetup] = useState(null);
  const [loadingLocalSetup, setLoadingLocalSetup] = useState(false);
  const [pullingModel, setPullingModel] = useState(null);

  // Embedding compatibility state
  const [embeddingStatus, setEmbeddingStatus] = useState(null);

  // Load embedding status when panel opens
  useEffect(() => {
    if (isOpen) {
      loadEmbeddingStatus();
    }
  }, [isOpen]);

  const loadEmbeddingStatus = async () => {
    try {
      const data = await api.getEmbeddingStatus();
      if (!data.error) {
        setEmbeddingStatus(data);
      }
    } catch (err) {
      console.error('Failed to load embedding status:', err);
    }
  };

  // Load OpenRouter models when provider is selected
  useEffect(() => {
    if (formData.embedding_provider === 'openrouter' || formData.chat_provider === 'openrouter') {
      loadOpenRouterModels();
    }
  }, [formData.embedding_provider, formData.chat_provider]);

  const loadOpenRouterModels = async () => {
    setLoadingModels(true);
    try {
      const data = await api.getOpenRouterModels();
      if (!data.error) {
        setAvailableModels({
          chat: data.chat_models || [],
          embedding: data.embedding_models || []
        });
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    } finally {
      setLoadingModels(false);
    }
  };

  // Load local setup info
  const loadLocalSetup = async () => {
    setLoadingLocalSetup(true);
    try {
      const data = await api.getLocalSetup();
      if (!data.error) {
        setLocalSetup(data);
      }
    } catch (err) {
      console.error('Failed to load local setup:', err);
    } finally {
      setLoadingLocalSetup(false);
    }
  };

  // Pull an Ollama model
  const handlePullModel = async (modelName) => {
    setPullingModel(modelName);
    try {
      await api.pullOllamaModel(modelName);
      // Refresh setup after a delay
      setTimeout(() => {
        loadLocalSetup();
        setPullingModel(null);
      }, 3000);
    } catch (err) {
      console.error('Failed to pull model:', err);
      setPullingModel(null);
    }
  };

  // Enable local mode (auto-configure based on hardware tier)
  const enableLocalMode = () => {
    if (localSetup?.recommendations?.provider_strategy) {
      const strategy = localSetup.recommendations.provider_strategy;
      const chatModel = localSetup.recommendations.chat?.recommended || 'llama3.2';
      const embedModel = localSetup.recommendations.embedding?.recommended || 'nomic-embed-text';
      setFormData({
        ...formData,
        embedding_provider: strategy.embedding_provider,
        chat_provider: strategy.chat_provider,
        ollama_model: chatModel,
        ollama_embedding_model: embedModel,
      });
    }
  };

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

          {/* Embedding Dimension Compatibility Warning */}
          {embeddingStatus?.has_dimension_mismatch && (
            <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-xl">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-amber-800">
                    Embedding Dimension Mismatch
                  </p>
                  <p className="text-xs text-amber-700 mt-1">
                    Your indexed documents use <strong>{embeddingStatus.collection?.dimension}D</strong> embeddings
                    ({embeddingStatus.collection?.model || 'unknown model'}), but your current config uses{' '}
                    <strong>{embeddingStatus.current?.dimension}D</strong> ({embeddingStatus.current?.model}).
                  </p>
                  <p className="text-xs text-amber-700 mt-2">
                    <strong>Options:</strong>
                  </p>
                  <ul className="text-xs text-amber-700 mt-1 ml-4 list-disc space-y-1">
                    <li>Switch to a compatible {embeddingStatus.collection?.dimension}D model (no re-indexing needed)</li>
                    <li>Clear index and re-index with your new model</li>
                  </ul>
                  {embeddingStatus.compatible_models?.length > 0 && (
                    <div className="mt-2 p-2 bg-white/50 rounded-lg">
                      <p className="text-xs font-medium text-amber-800">Compatible {embeddingStatus.collection?.dimension}D models:</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {embeddingStatus.compatible_models.map(m => (
                          <span key={m.id} className="text-xs px-2 py-0.5 bg-amber-100 rounded text-amber-800">
                            {m.name} ({m.provider})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Current Collection Info */}
          {embeddingStatus?.collection?.document_count > 0 && !embeddingStatus?.has_dimension_mismatch && (
            <div className="p-3 bg-sage-50 border border-sage-200 rounded-lg">
              <div className="flex items-center gap-2 text-sm text-sage-700">
                <Layers className="w-4 h-4" />
                <span>
                  Indexed: <strong>{embeddingStatus.collection.document_count}</strong> docs using{' '}
                  <strong>{embeddingStatus.collection.dimension}D</strong> embeddings
                  {embeddingStatus.collection.model && ` (${embeddingStatus.collection.model})`}
                </span>
              </div>
            </div>
          )}

          {/* OpenRouter API Key - Featured */}
          <div className="p-4 bg-gradient-to-br from-ember-50 to-sage-50 rounded-xl border-2 border-ember-200">
            <label className="block text-sm font-semibold text-ink-800 mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-ember-600" />
              OpenRouter API Key (Recommended)
              {config?.has_openrouter_key && (
                <span className="ml-auto text-sage-600 text-xs font-normal">(configured)</span>
              )}
            </label>
            <input
              type="password"
              className="input-field mb-2"
              placeholder="sk-or-v1-..."
              value={formData.openrouter_api_key}
              onChange={(e) => setFormData({ ...formData, openrouter_api_key: e.target.value })}
            />
            <p className="text-xs text-ink-600">
              🌐 Access 200+ models: Claude, GPT-4, Gemini, Llama, and more with one key
            </p>
          </div>

          {/* Legacy Provider Keys - Collapsible */}
          <details className="p-4 bg-parchment-50 rounded-lg">
            <summary className="cursor-pointer text-sm font-medium text-ink-700 flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Direct Provider Keys (Optional)
            </summary>
            <div className="mt-4 space-y-4">
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
            </div>
          </details>

          {/* Provider Selection */}
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
                <option value="openrouter">🌐 OpenRouter (All Models)</option>
                <option value="openai">OpenAI (Direct)</option>
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
                <option value="openrouter">🌐 OpenRouter (All Models)</option>
                <option value="anthropic">Anthropic (Direct)</option>
                <option value="openai">OpenAI (Direct)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
          </div>

          {/* OpenRouter Model Selection */}
          {(formData.embedding_provider === 'openrouter' || formData.chat_provider === 'openrouter') && (
            <div className="p-4 bg-gradient-to-br from-ember-50 to-sage-50 rounded-lg space-y-4">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-ember-600" />
                <span className="text-sm font-medium text-ink-700">Model Selection</span>
                {loadingModels && <span className="text-xs text-ink-500 animate-pulse">Loading models...</span>}
              </div>

              {formData.chat_provider === 'openrouter' && (
                <div>
                  <label className="block text-xs text-ink-600 mb-1 font-medium">Chat Model</label>
                  <select
                    className="input-field py-2 text-sm"
                    value={formData.openrouter_chat_model}
                    onChange={(e) => setFormData({ ...formData, openrouter_chat_model: e.target.value })}
                  >
                    <optgroup label="⭐ Recommended">
                      <option value="anthropic/claude-sonnet-4">Claude Sonnet 4 (Best Reasoning)</option>
                      <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free)</option>
                      <option value="openai/gpt-4o">GPT-4o (Fast & Smart)</option>
                      <option value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B (Open Source)</option>
                      <option value="google/gemini-pro-1.5">Gemini Pro 1.5</option>
                      <option value="anthropic/claude-opus-4">Claude Opus 4 (Most Capable)</option>
                    </optgroup>
                    {availableModels.chat.length > 0 && (
                      <optgroup label="All Available Models">
                        {availableModels.chat.slice(0, 50).map(model => (
                          <option key={model.id} value={model.id}>
                            {model.name}
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                </div>
              )}

              {formData.embedding_provider === 'openrouter' && (
                <div>
                  <label className="block text-xs text-ink-600 mb-1 font-medium">Embedding Model</label>
                  <select
                    className="input-field py-2 text-sm"
                    value={formData.openrouter_embedding_model}
                    onChange={(e) => setFormData({ ...formData, openrouter_embedding_model: e.target.value })}
                  >
                    <optgroup label="⭐ Recommended">
                      <option value="openai/text-embedding-3-small">OpenAI Small (Fast, 1536 dims)</option>
                      <option value="openai/text-embedding-3-large">OpenAI Large (Best, 3072 dims)</option>
                    </optgroup>
                    {availableModels.embedding.length > 0 && (
                      <optgroup label="All Available Models">
                        {availableModels.embedding.map(model => (
                          <option key={model.id} value={model.id}>
                            {model.name}
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                </div>
              )}

              <p className="text-xs text-ink-500 flex items-center gap-1">
                <Lightbulb className="w-3 h-3" />
                Tip: Try different models! Each has unique strengths.
              </p>
            </div>
          )}

          {/* Local Mode Setup Section */}
          <details className="p-4 bg-gradient-to-br from-sage-50 to-parchment-50 rounded-xl border border-sage-200">
            <summary className="cursor-pointer text-sm font-semibold text-ink-800 flex items-center gap-2">
              <Zap className="w-4 h-4 text-sage-600" />
              Local Mode Setup (100% Offline)
              {localSetup?.ready_for_local?.fully_ready && (
                <span className="ml-auto text-sage-600 text-xs flex items-center gap-1">
                  <Check className="w-3 h-3" /> Ready
                </span>
              )}
            </summary>

            <div className="mt-4 space-y-4">
              {!localSetup && !loadingLocalSetup && (
                <button
                  onClick={loadLocalSetup}
                  className="btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <Monitor className="w-4 h-4" />
                  Detect My Hardware
                </button>
              )}

              {loadingLocalSetup && (
                <div className="text-center py-4 text-ink-500">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                  <p className="text-sm">Detecting hardware...</p>
                </div>
              )}

              {localSetup && !loadingLocalSetup && (
                <>
                  {/* Hardware Info */}
                  <div className="p-3 bg-white rounded-lg border border-parchment-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-ink-600 flex items-center gap-1">
                        <Cpu className="w-3 h-3" /> System
                      </span>
                      <button onClick={loadLocalSetup} className="text-ink-400 hover:text-ink-600">
                        <RefreshCw className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-ink-500">CPU:</span>
                        <span className="ml-1 text-ink-700">{localSetup.hardware?.system?.cpu_count} cores</span>
                      </div>
                      <div>
                        <span className="text-ink-500">RAM:</span>
                        <span className="ml-1 text-ink-700">{localSetup.hardware?.system?.available_ram_gb?.toFixed(1)} GB free</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-ink-500">GPU:</span>
                        <span className="ml-1 text-ink-700">
                          {localSetup.hardware?.gpu?.has_gpu
                            ? `${localSetup.hardware.gpu.gpu_type} (${localSetup.hardware.gpu.vram_gb} GB)`
                            : 'No dedicated GPU'
                          }
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Hardware Tier & Recommendation */}
                  <div className="p-3 bg-white rounded-lg border border-parchment-200">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium">
                        {localSetup.recommendations?.tier_description}
                      </span>
                    </div>

                    {/* Provider Strategy */}
                    {localSetup.recommendations?.provider_strategy && (
                      <div className="mt-2 p-2 bg-parchment-50 rounded-lg space-y-1">
                        <p className="text-xs font-medium text-ink-700">
                          Recommended: {localSetup.recommendations.provider_strategy.recommended === 'local'
                            ? '🖥️ Full Local'
                            : localSetup.recommendations.provider_strategy.recommended === 'hybrid'
                              ? '🔀 Hybrid (Local + Cloud)'
                              : '☁️ Cloud'}
                        </p>
                        <p className="text-xs text-ink-500">
                          {localSetup.recommendations.provider_strategy.reason}
                        </p>
                        <div className="grid grid-cols-2 gap-1 mt-2 text-xs">
                          <span>{localSetup.recommendations.provider_strategy.expected_speed}</span>
                          <span>{localSetup.recommendations.provider_strategy.privacy}</span>
                          <span className="col-span-2">{localSetup.recommendations.provider_strategy.cost}</span>
                        </div>
                      </div>
                    )}

                    {/* Download Info */}
                    {localSetup.recommendations?.download_info && localSetup.recommendations.provider_strategy?.recommended !== 'cloud' && (
                      <div className="mt-2 p-2 bg-amber-50 rounded-lg">
                        <p className="text-xs font-medium text-amber-800 flex items-center gap-1">
                          <Download className="w-3 h-3" />
                          Download Required: {localSetup.recommendations.download_info.total_size_gb} GB
                        </p>
                        <p className="text-xs text-amber-700 mt-1">
                          {localSetup.recommendations.download_info.estimated_download_time} •
                          Stored in {localSetup.recommendations.download_info.storage_location}
                        </p>
                        <p className="text-xs text-amber-600 mt-1">
                          Source: {localSetup.recommendations.download_info.download_source}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Ollama Status */}
                  <div className="p-3 bg-white rounded-lg border border-parchment-200">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-ink-600 flex items-center gap-1">
                        <HardDrive className="w-3 h-3" /> Ollama
                      </span>
                      {localSetup.ollama?.running ? (
                        <span className="text-xs text-sage-600 flex items-center gap-1">
                          <Wifi className="w-3 h-3" /> Running
                        </span>
                      ) : localSetup.ollama?.installed ? (
                        <span className="text-xs text-amber-600 flex items-center gap-1">
                          <WifiOff className="w-3 h-3" /> Not Running
                        </span>
                      ) : (
                        <span className="text-xs text-red-600 flex items-center gap-1">
                          <X className="w-3 h-3" /> Not Installed
                        </span>
                      )}
                    </div>

                    {!localSetup.ollama?.installed && (
                      <p className="text-xs text-ink-500 mt-2">
                        Install Ollama from <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer" className="text-ember-600 underline">ollama.ai</a>
                      </p>
                    )}
                  </div>

                  {/* Recommended Models */}
                  {localSetup.ollama?.running && (
                    <div className="p-3 bg-white rounded-lg border border-parchment-200 space-y-3">
                      <span className="text-xs font-medium text-ink-600">Recommended Models</span>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-xs text-ink-700 font-medium">Chat: {localSetup.recommendations?.chat?.recommended}</p>
                            <p className="text-xs text-ink-500">{localSetup.recommendations?.chat?.info?.description}</p>
                          </div>
                          {localSetup.ready_for_local?.has_chat_model ? (
                            <Check className="w-4 h-4 text-sage-600" />
                          ) : (
                            <button
                              onClick={() => handlePullModel(localSetup.recommendations?.chat?.recommended)}
                              disabled={pullingModel}
                              className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
                            >
                              {pullingModel === localSetup.recommendations?.chat?.recommended ? (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              ) : (
                                <Download className="w-3 h-3" />
                              )}
                              Install
                            </button>
                          )}
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-xs text-ink-700 font-medium">Embedding: {localSetup.recommendations?.embedding?.recommended}</p>
                            <p className="text-xs text-ink-500">{localSetup.recommendations?.embedding?.info?.description}</p>
                          </div>
                          {localSetup.ready_for_local?.has_embedding_model ? (
                            <Check className="w-4 h-4 text-sage-600" />
                          ) : (
                            <button
                              onClick={() => handlePullModel(localSetup.recommendations?.embedding?.recommended)}
                              disabled={pullingModel}
                              className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
                            >
                              {pullingModel === localSetup.recommendations?.embedding?.recommended ? (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              ) : (
                                <Download className="w-3 h-3" />
                              )}
                              Install
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Enable Local Mode Button */}
                  {localSetup.ollama?.running && (
                    <button
                      onClick={enableLocalMode}
                      className="w-full btn-primary flex items-center justify-center gap-2"
                    >
                      <Zap className="w-4 h-4" />
                      Enable Local Mode
                    </button>
                  )}
                </>
              )}
            </div>
          </details>

          {/* Ollama Settings */}
          {(formData.embedding_provider === 'ollama' || formData.chat_provider === 'ollama') && (
            <div className="p-4 bg-parchment-100 rounded-lg space-y-4">
              <p className="text-sm text-ink-600 font-medium">Ollama Settings (Local Models)</p>
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
                  Chat Model Name
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.ollama_model}
                  onChange={(e) => setFormData({ ...formData, ollama_model: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-2">
                  Embedding Model Name
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.ollama_embedding_model}
                  onChange={(e) => setFormData({ ...formData, ollama_embedding_model: e.target.value })}
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
          className={`rounded-2xl px-4 py-3 ${isUser
            ? 'bg-ember-500 text-white rounded-tr-md'
            : 'bg-white border border-parchment-200 shadow-paper rounded-tl-md'
            }`}
        >
          <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : 'prose-ink'}`}>
            <ReactMarkdown
              components={{
                // Custom heading styles
                h1: ({ node, ...props }) => <h1 className="text-lg font-bold mt-3 mb-2 first:mt-0" {...props} />,
                h2: ({ node, ...props }) => <h2 className="text-base font-bold mt-3 mb-2 first:mt-0" {...props} />,
                h3: ({ node, ...props }) => <h3 className="text-sm font-bold mt-2 mb-1 first:mt-0" {...props} />,
                // Paragraph styling
                p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                // List styling
                ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
                li: ({ node, ...props }) => <li className="ml-2" {...props} />,
                // Strong/bold styling
                strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                // Code styling
                code: ({ node, inline, ...props }) =>
                  inline
                    ? <code className={`px-1 py-0.5 rounded text-sm font-mono ${isUser ? 'bg-white/20' : 'bg-parchment-100'}`} {...props} />
                    : <code className={`block p-2 rounded text-sm font-mono overflow-x-auto ${isUser ? 'bg-white/20' : 'bg-parchment-100'}`} {...props} />,
                pre: ({ node, ...props }) => <pre className="mb-2 last:mb-0" {...props} />,
                // Link styling
                a: ({ node, ...props }) => <a className={`underline ${isUser ? 'text-white' : 'text-ember-600 hover:text-ember-700'}`} {...props} />,
                // Blockquote styling
                blockquote: ({ node, ...props }) => <blockquote className={`border-l-2 pl-3 italic ${isUser ? 'border-white/50' : 'border-ink-300'}`} {...props} />,
              }}
            >
              {message}
            </ReactMarkdown>
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
// Folder Browser Component
// ============================================================================

function FolderBrowser({ value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState(null);
  const [parentPath, setParentPath] = useState(null);
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Load directory contents
  const loadDirectory = async (path = null) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.browseDirectory(path);
      setCurrentPath(result.path);
      setParentPath(result.parent);
      setItems(result.items || []);
    } catch (err) {
      setError(err.message || 'Failed to load directory');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  // Open dropdown and load initial directory
  const handleOpen = () => {
    if (!isOpen) {
      loadDirectory(value || null);
    }
    setIsOpen(!isOpen);
  };

  // Navigate to a folder
  const handleNavigate = (path) => {
    loadDirectory(path);
  };

  // Select and close
  const handleSelect = () => {
    if (currentPath) {
      onChange(currentPath);
    }
    setIsOpen(false);
  };

  // Get icon for item type
  const getIcon = (item) => {
    if (item.type === 'shortcut') {
      const iconMap = {
        'Home': '🏠',
        'Desktop': '🖥️',
        'Documents': '📄',
        'Downloads': '📥',
      };
      return iconMap[item.name] || '📁';
    }
    if (item.type === 'drive') return '💾';
    if (item.type === 'file') {
      const extIconMap = {
        '.pdf': '📕',
        '.doc': '📘', '.docx': '📘',
        '.ppt': '📙', '.pptx': '📙',
        '.txt': '📝', '.md': '📝',
        '.py': '🐍', '.js': '📜', '.jsx': '📜', '.ts': '📜', '.tsx': '📜',
        '.json': '📋', '.yaml': '📋', '.yml': '📋',
        '.html': '🌐', '.css': '🎨',
      };
      return extIconMap[item.extension] || '📄';
    }
    return item.is_hidden ? '📁' : '📂';
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Selected Path Display / Trigger */}
      <button
        type="button"
        onClick={handleOpen}
        className="input-field w-full text-left flex items-center gap-2 cursor-pointer hover:border-ember-300 transition-colors"
      >
        <FolderTree className="w-4 h-4 text-ink-400 flex-shrink-0" />
        <span className={`flex-1 truncate font-mono text-sm ${value ? 'text-ink-800' : 'text-ink-400'}`}>
          {value || 'Browse folders...'}
        </span>
        <ChevronDown className={`w-4 h-4 text-ink-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl border border-parchment-200 shadow-floating z-50 overflow-hidden"
          >
            {/* Header with current path */}
            <div className="px-3 py-2 bg-parchment-50 border-b border-parchment-200">
              <div className="flex items-center gap-2">
                {parentPath && (
                  <button
                    onClick={() => handleNavigate(parentPath)}
                    className="p-1 hover:bg-parchment-200 rounded transition-colors"
                    title="Go up"
                  >
                    <ChevronRight className="w-4 h-4 text-ink-500 rotate-180" />
                  </button>
                )}
                <div className="flex-1 text-xs font-mono text-ink-600 truncate">
                  {currentPath || 'Quick Access'}
                </div>
                {!parentPath && (
                  <button
                    onClick={() => loadDirectory(null)}
                    className="p-1 hover:bg-parchment-200 rounded transition-colors"
                    title="Go to root"
                  >
                    <RefreshCw className="w-3 h-3 text-ink-400" />
                  </button>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="py-8 text-center text-ink-500">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                  <span className="text-sm">Loading...</span>
                </div>
              ) : error ? (
                <div className="py-6 px-4 text-center text-red-600">
                  <AlertCircle className="w-5 h-5 mx-auto mb-2" />
                  <span className="text-sm">{error}</span>
                </div>
              ) : items.length === 0 ? (
                <div className="py-8 text-center text-ink-500">
                  <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <span className="text-sm">No indexable files found</span>
                </div>
              ) : (
                <div className="py-1">
                  {items.map((item, index) => (
                    <button
                      key={item.path || index}
                      onClick={() => {
                        if (item.is_dir) {
                          handleNavigate(item.path);
                        } else {
                          // For files, select directly
                          onChange(item.path);
                          setIsOpen(false);
                        }
                      }}
                      className={`w-full px-3 py-2 flex items-center gap-2 hover:bg-parchment-50 transition-colors text-left ${item.is_hidden ? 'opacity-60' : ''
                        } ${item.type === 'file' ? 'bg-parchment-25' : ''}`}
                    >
                      <span className="text-base">{getIcon(item)}</span>
                      <span className={`flex-1 text-sm truncate ${item.type === 'file' ? 'text-ink-600' : 'text-ink-700'}`}>{item.name}</span>
                      {item.is_dir ? (
                        <ChevronRight className="w-4 h-4 text-ink-300" />
                      ) : (
                        <span className="text-xs text-ink-400">{item.extension}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer with Select button */}
            {currentPath && (
              <div className="px-3 py-2 bg-parchment-50 border-t border-parchment-200 flex justify-end gap-2">
                <button
                  onClick={() => setIsOpen(false)}
                  className="btn-ghost text-sm py-1 px-3"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSelect}
                  className="btn-primary text-sm py-1 px-3 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  Select
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
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
  const [conversationId, setConversationId] = useState(() => {
    // Restore from localStorage
    return localStorage.getItem('knowledgeai-current-conversation') || null;
  });
  const [chatLoading, setChatLoading] = useState(false);
  const [conversations, setConversations] = useState([]);

  // Tutor state
  const [tutorMode, setTutorMode] = useState('quiz');
  const [tutorTopic, setTutorTopic] = useState('');
  const [tutorResult, setTutorResult] = useState(null);
  const [tutorLoading, setTutorLoading] = useState(false);

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // { current: 0, total: 0, filename: '' }

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    // Filter for files only (rough check)
    const validFiles = files; // Server will reject unsupported types

    if (validFiles.length === 0) return;

    setUploadProgress({ current: 0, total: validFiles.length, filename: '' });

    let uploadedCount = 0;
    let errors = [];

    for (let i = 0; i < validFiles.length; i++) {
      const file = validFiles[i];
      setUploadProgress({ current: i + 1, total: validFiles.length, filename: file.name });

      try {
        await api.uploadFile(file, activeKnowledgeBase);
        uploadedCount++;
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err);
        errors.push(`${file.name}: ${err.message}`);
      }
    }

    setUploadProgress(null);

    // Refresh data
    if (uploadedCount > 0) {
      await loadFiles();
      await loadStats();
      // Show success notification (we can use alert for now or a toast if available, sticking to alert for simplicity as per plan)
      // alert(`Successfully uploaded ${uploadedCount} files.`);
    }

    if (errors.length > 0) {
      alert(`Failed to upload ${errors.length} files:\n${errors.join('\n')}`);
    }
  };

  // Index state
  const [indexPath, setIndexPath] = useState('');
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState(null);
  const [filterPreset, setFilterPreset] = useState('auto');
  const [checkSensitive, setCheckSensitive] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState(null);

  // Knowledge base state
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [activeKnowledgeBase, setActiveKnowledgeBase] = useState(() => {
    return localStorage.getItem('knowledgeai-active-kb') || null;
  });
  const [searchAllKBs, setSearchAllKBs] = useState(false);
  const [showCreateKBModal, setShowCreateKBModal] = useState(false);
  const [newKBName, setNewKBName] = useState('');
  const [newKBDescription, setNewKBDescription] = useState('');
  const [creatingKB, setCreatingKB] = useState(false);

  // Refs
  const chatEndRef = useRef(null);
  const chatInputRef = useRef(null);

  // State for confirm modal
  const confirmCallback = useRef(null);
  const [confirmState, setConfirmState] = useState({
    isOpen: false,
    title: '',
    message: ''
  });

  const confirmAction = (title, message, action) => {
    confirmCallback.current = action;
    setConfirmState({
      isOpen: true,
      title,
      message
    });
  };

  const handleConfirm = async () => {
    if (confirmCallback.current) {
      try {
        await confirmCallback.current();
        setConfirmState(prev => ({ ...prev, isOpen: false }));
      } catch (e) {
        console.error(e);
        alert("Action failed: " + e.message);
      }
    } else {
      setConfirmState(prev => ({ ...prev, isOpen: false }));
    }
  };

  // Initial data loading
  useEffect(() => {
    loadConfig();
    loadStats();
    loadFiles();
    loadConversations();
    loadKnowledgeBases();
  }, []);

  // Restore conversation on mount if conversationId exists
  useEffect(() => {
    if (conversationId && messages.length === 0) {
      loadConversation(conversationId);
    }
  }, []);

  // Persist conversationId to localStorage
  useEffect(() => {
    if (conversationId) {
      localStorage.setItem('knowledgeai-current-conversation', conversationId);
    } else {
      localStorage.removeItem('knowledgeai-current-conversation');
    }
  }, [conversationId]);

  // Persist activeKnowledgeBase to localStorage
  useEffect(() => {
    if (activeKnowledgeBase) {
      localStorage.setItem('knowledgeai-active-kb', activeKnowledgeBase);
    } else {
      localStorage.removeItem('knowledgeai-active-kb');
    }
  }, [activeKnowledgeBase]);

  // Reload stats and files when knowledge base changes
  useEffect(() => {
    if (activeKnowledgeBase) {
      loadStats();
      loadFiles();
    }
  }, [activeKnowledgeBase]);


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
      const data = await api.getStats(activeKnowledgeBase);
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadFiles = async () => {
    try {
      const data = await api.getFiles(activeKnowledgeBase);
      setFiles(data.files || []);
    } catch (err) {
      console.error('Failed to load files:', err);
    }
  };

  const loadKnowledgeBases = async () => {
    try {
      const data = await api.getKnowledgeBases();
      setKnowledgeBases(data.knowledge_bases || []);

      // If no active KB set, use the first one
      if (!activeKnowledgeBase && data.knowledge_bases?.length > 0) {
        setActiveKnowledgeBase(data.knowledge_bases[0].id);
      }
    } catch (err) {
      console.error('Failed to load knowledge bases:', err);
    }
  };

  const handleCreateKnowledgeBase = async () => {
    if (!newKBName.trim()) return;

    setCreatingKB(true);
    try {
      const result = await api.createKnowledgeBase(newKBName.trim(), newKBDescription.trim() || null);
      setShowCreateKBModal(false);
      setNewKBName('');
      setNewKBDescription('');
      await loadKnowledgeBases();
      setActiveKnowledgeBase(result.id);
    } catch (err) {
      console.error('Failed to create knowledge base:', err);
    } finally {
      setCreatingKB(false);
    }
  };

  const handleDeleteKnowledgeBase = (kbId, e) => {
    e?.stopPropagation();

    confirmAction(
      'Delete Knowledge Base',
      'Are you sure you want to delete this knowledge base? All indexed files will be removed. This action cannot be undone.',
      async () => {
        try {
          await api.deleteKnowledgeBase(kbId);

          if (activeKnowledgeBase === kbId) {
            const remaining = knowledgeBases.filter(kb => kb.id !== kbId);
            if (remaining.length > 0) {
              setActiveKnowledgeBase(remaining[0].id);
            } else {
              setActiveKnowledgeBase(null);
            }
          }
          await loadKnowledgeBases();
        } catch (err) {
          console.error('Failed to delete knowledge base:', err);
          throw err; // Propagate to modal error handler
        }
      }
    );
  };

  const loadConversations = async () => {
    try {
      const data = await api.getConversations();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const loadConversation = async (id) => {
    try {
      const data = await api.getConversation(id);
      setMessages(data.messages || []);
      setConversationId(id);
    } catch (err) {
      console.error('Failed to load conversation:', err);
      // If conversation not found, start fresh
      setMessages([]);
      setConversationId(null);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setActiveTab('chat');
  };

  const switchConversation = async (id) => {
    if (id === conversationId) return;
    await loadConversation(id);
    setActiveTab('chat');
  };

  const handleDeleteConversation = async (id, e) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      if (id === conversationId) {
        setMessages([]);
        setConversationId(null);
      }
      loadConversations();
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Search handler
  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    try {
      const results = await api.search(searchQuery, {
        knowledgeBaseId: activeKnowledgeBase,
        searchAll: searchAllKBs,
      });
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
        knowledgeBaseId: activeKnowledgeBase,
        searchAll: searchAllKBs,
        conversationId,
        mode: chatMode,
      });

      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.response, sources: response.sources },
      ]);
      // Refresh conversation list to show new/updated conversation
      loadConversations();
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
        knowledgeBaseId: activeKnowledgeBase,
        filterPreset,
        checkSensitiveContent: checkSensitive,
      });
      setIndexResult(result);
      loadStats();
      loadFiles();
      loadKnowledgeBases();
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
    <div
      className="min-h-screen flex relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag Overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-4 z-50 bg-ember-500/90 backdrop-blur-sm border-4 border-dashed border-white/50 rounded-2xl flex items-center justify-center pointer-events-none"
          >
            <div className="text-center text-white">
              <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-white/20 flex items-center justify-center">
                <Upload className="w-12 h-12" />
              </div>
              <h3 className="text-3xl font-display font-bold mb-2">
                Drop files to upload
              </h3>
              <p className="text-white/80 text-lg">
                Add to {knowledgeBases.find(kb => kb.id === activeKnowledgeBase)?.name || 'Knowledge Base'}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Progress Overlay */}
      <AnimatePresence>
        {uploadProgress && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 z-50 bg-white shadow-xl rounded-xl p-4 border border-parchment-200 w-80"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-ember-100 flex items-center justify-center text-ember-600">
                <Upload className="w-5 h-5 animate-bounce" />
              </div>
              <div>
                <h4 className="font-semibold text-ink-900">Uploading Files...</h4>
                <p className="text-xs text-ink-500">
                  {uploadProgress.current} of {uploadProgress.total}
                </p>
              </div>
            </div>
            <div className="mb-2">
              <div className="h-1.5 w-full bg-parchment-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-ember-500 transition-all duration-300"
                  style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                />
              </div>
            </div>
            <p className="text-xs text-ink-400 truncate">
              Processing: {uploadProgress.filename}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
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
        <nav className="p-4 border-b border-parchment-200">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === item.id
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

        {/* Knowledge Bases */}
        <div className="px-4 py-3 border-b border-parchment-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-ink-500 uppercase tracking-wide">Knowledge Base</span>
            <button
              onClick={() => setShowCreateKBModal(true)}
              className="p-1 rounded-md text-ink-400 hover:text-ember-600 hover:bg-parchment-100 transition-colors"
              title="New Knowledge Base"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* KB List */}
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {knowledgeBases.map((kb) => (
              <div
                key={kb.id}
                className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg transition-all ${activeKnowledgeBase === kb.id
                  ? 'bg-sage-100 text-sage-800'
                  : 'hover:bg-parchment-100 text-ink-600'
                  }`}
              >
                {/* Selectable Area */}
                <div
                  className="flex-1 flex items-center gap-2 min-w-0 cursor-pointer"
                  onClick={() => setActiveKnowledgeBase(kb.id)}
                >
                  <Database className="w-4 h-4 flex-shrink-0 opacity-60" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{kb.name}</p>
                    <p className="text-xs opacity-70">{kb.document_count} {kb.document_count === 1 ? 'file' : 'files'}</p>
                  </div>
                </div>

                {/* Delete Button - Separate from click area */}
                {knowledgeBases.length > 1 && (
                  <div
                    role="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      console.log('Delete clicked for:', kb.id);
                      handleDeleteKnowledgeBase(kb.id, e);
                    }}
                    className="p-1.5 rounded opacity-40 hover:opacity-100 text-ink-400 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer z-20"
                    title="Delete Knowledge Base"
                  >
                    <Trash2 className="w-4 h-4 pointer-events-none" />
                  </div>
                )}
              </div>
            ))}
          </div>

          <label className="flex items-center gap-2 mt-3 text-xs text-ink-500">
            <input
              type="checkbox"
              checked={searchAllKBs}
              onChange={(e) => setSearchAllKBs(e.target.checked)}
              className="rounded text-ember-500 focus:ring-ember-300"
            />
            Search all knowledge bases
          </label>
        </div>

        {/* Conversations List */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 py-3 flex items-center justify-between">
            <span className="text-xs font-medium text-ink-500 uppercase tracking-wide">Conversations</span>
            <button
              onClick={startNewConversation}
              className="p-1 rounded-md text-ink-400 hover:text-ember-600 hover:bg-parchment-100 transition-colors"
              title="New Chat"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2">
            {conversations.length === 0 ? (
              <p className="text-xs text-ink-400 text-center px-4 py-6">No conversations yet</p>
            ) : (
              <ul className="space-y-1">
                {conversations.map((conv) => (
                  <li key={conv.id}>
                    <div
                      onClick={() => switchConversation(conv.id)}
                      className={`w-full group flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-all cursor-pointer ${conversationId === conv.id
                        ? 'bg-ember-50 text-ember-700'
                        : 'text-ink-600 hover:bg-parchment-100'
                        }`}
                    >
                      <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-50" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{conv.title}</p>
                        <p className="text-xs text-ink-400">
                          {conv.message_count} messages
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleDeleteConversation(conv.id, e);
                        }}
                        className="p-1.5 rounded opacity-40 hover:opacity-100 text-ink-400 hover:text-red-500 hover:bg-red-50 transition-all"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

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
      </aside >

      {/* Main Content */}
      < main className="flex-1 flex flex-col" >
        {/* Chat Tab */}
        {
          activeTab === 'chat' && (
            <div className="flex-1 flex flex-col">
              {/* Chat Header */}
              <header className="px-6 py-4 border-b border-parchment-200 bg-white/80 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-display text-lg font-semibold text-ink-900">Chat with Your Knowledge</h2>
                    <div className="flex items-center gap-2 text-sm text-ink-500">
                      <Database className="w-3.5 h-3.5" />
                      <span>Using: </span>
                      <span className="font-medium text-ink-700 bg-parchment-100 px-2 py-0.5 rounded-md">
                        {searchAllKBs
                          ? 'All Knowledge Bases'
                          : knowledgeBases.find(kb => kb.id === activeKnowledgeBase)?.name || 'General'}
                      </span>
                    </div>
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
          )
        }

        {/* Search Tab */}
        {
          activeTab === 'search' && (
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
          )
        }

        {/* Tutor Tab */}
        {
          activeTab === 'tutor' && (
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
                        className={`p-4 rounded-xl border-2 transition-all ${tutorMode === mode.id
                          ? 'border-ember-500 bg-ember-50'
                          : 'border-parchment-200 hover:border-parchment-300'
                          }`}
                      >
                        <mode.icon className={`w-6 h-6 mx-auto mb-2 ${tutorMode === mode.id ? 'text-ember-600' : 'text-ink-400'
                          }`} />
                        <span className={`text-sm font-medium ${tutorMode === mode.id ? 'text-ember-700' : 'text-ink-600'
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
          )
        }

        {/* Files Tab */}
        {
          activeTab === 'files' && (
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
                  <div className="space-y-3 mb-4">
                    {/* Folder Browser */}
                    <FolderBrowser
                      value={indexPath}
                      onChange={setIndexPath}
                    />

                    {/* Manual Path Input (optional fallback) */}
                    <details className="text-sm">
                      <summary className="text-ink-500 hover:text-ink-700 cursor-pointer flex items-center gap-1">
                        <span>Or enter path manually</span>
                      </summary>
                      <input
                        type="text"
                        value={indexPath}
                        onChange={(e) => setIndexPath(e.target.value)}
                        placeholder="/path/to/your/documents or ~/Documents"
                        className="input-field flex-1 font-mono text-sm mt-2"
                      />
                    </details>
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
                    className={`mb-6 p-4 rounded-lg max-w-2xl ${indexResult.error
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
                        onClick={() => {
                          confirmAction(
                            'Clear Index',
                            `Are you sure you want to clear all ${files.length} files from ${activeKnowledgeBase ? 'the current knowledge base' : 'the general index'}? This cannot be undone.`,
                            async () => {
                              await api.clearIndex(activeKnowledgeBase);
                              await loadStats();
                              await loadFiles();
                              await loadKnowledgeBases();
                            }
                          );
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
                          className="flex items-center gap-3 p-3 bg-white rounded-lg border border-parchment-200 group"
                        >
                          <FileText className="w-5 h-5 text-ink-400 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-ink-800 truncate">{file.name}</p>
                            <p className="text-xs text-ink-400 truncate">{file.path}</p>
                          </div>
                          <span className="tag">{file.chunks} chunks</span>
                          <span className="tag tag-sage">{file.type}</span>

                          <button
                            onClick={() => {
                              confirmAction(
                                'Remove File',
                                `Are you sure you want to remove "${file.name}" from the index?`,
                                async () => {
                                  try {
                                    await api.removeFile(file.hash, activeKnowledgeBase, file.path);
                                    await loadStats();
                                    await loadFiles();
                                    await loadKnowledgeBases();
                                  } catch (err) {
                                    console.error('Failed to remove file:', err);
                                    throw err;
                                  }
                                }
                              );
                            }}
                            className="p-1.5 text-ink-400 hover:text-red-600 hover:bg-red-50 rounded transition-all"
                            title="Remove file"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        }
      </main >

      {/* Confirm Modal */}
      {confirmState.isOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden"
          >
            <div className="p-6">
              <h3 className="text-lg font-semibold text-ink-900 mb-2">{confirmState.title}</h3>
              <p className="text-ink-600 mb-6">{confirmState.message}</p>

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setConfirmState(prev => ({ ...prev, isOpen: false }))}
                  className="px-4 py-2 text-ink-600 font-medium hover:bg-parchment-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors shadow-sm"
                >
                  Confirm Delete
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Config Modal */}
      < AnimatePresence >
        <ConfigPanel
          isOpen={configOpen}
          onClose={() => setConfigOpen(false)}
          config={config}
          onConfigUpdate={loadConfig}
        />
      </AnimatePresence >

      {/* Create Knowledge Base Modal */}
      < AnimatePresence >
        {showCreateKBModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
            onClick={() => setShowCreateKBModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden"
            >
              <div className="p-6 border-b border-parchment-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sage-500 to-sage-600 flex items-center justify-center">
                    <Database className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="font-display font-semibold text-ink-900">Create Knowledge Base</h2>
                    <p className="text-sm text-ink-500">Organize your documents by topic</p>
                  </div>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-ink-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={newKBName}
                    onChange={(e) => setNewKBName(e.target.value)}
                    placeholder="e.g., Bio 101, Work Projects"
                    className="w-full px-4 py-3 border border-parchment-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-ember-300"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-700 mb-1">Description (optional)</label>
                  <textarea
                    value={newKBDescription}
                    onChange={(e) => setNewKBDescription(e.target.value)}
                    placeholder="Brief description of what this knowledge base contains"
                    rows={2}
                    className="w-full px-4 py-3 border border-parchment-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-ember-300 resize-none"
                  />
                </div>
              </div>

              <div className="p-6 pt-0 flex gap-3">
                <button
                  onClick={() => {
                    setShowCreateKBModal(false);
                    setNewKBName('');
                    setNewKBDescription('');
                  }}
                  className="flex-1 px-4 py-3 border border-parchment-200 rounded-xl text-ink-600 hover:bg-parchment-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateKnowledgeBase}
                  disabled={!newKBName.trim() || creatingKB}
                  className="flex-1 px-4 py-3 bg-ember-500 text-white rounded-xl hover:bg-ember-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {creatingKB ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Create
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )
        }
      </AnimatePresence >
    </div >
  );
}
