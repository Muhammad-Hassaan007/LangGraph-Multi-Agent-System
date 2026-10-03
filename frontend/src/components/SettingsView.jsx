import React, { useState } from 'react';
import { 
  Settings, 
  Cpu, 
  Database, 
  Clock, 
  Trash2, 
  RotateCw, 
  CheckCircle2, 
  Sliders, 
  User, 
  ShieldCheck,
  Sparkles,
  Info,
  AlertTriangle,
  Loader2
} from 'lucide-react';

export default function SettingsView({ 
  onClearChat, 
  onRefreshDocs,
  onDeleteAllDocs,
  documentsCount = 0 
}) {
  const [clearedToast, setClearedToast] = useState('');
  const [refreshedToast, setRefreshedToast] = useState('');
  const [deletedAllToast, setDeletedAllToast] = useState('');
  const [deletingAll, setDeletingAll] = useState(false);

  const handleClearChatHistory = () => {
    if (window.confirm('Clear all conversation messages in the chat window?')) {
      if (onClearChat) onClearChat();
      setClearedToast('Conversation history has been cleared.');
      setTimeout(() => setClearedToast(''), 3000);
    }
  };

  const handleRefreshKnowledgeBase = () => {
    if (onRefreshDocs) onRefreshDocs();
    setRefreshedToast('Knowledge base re-synced with Supabase.');
    setTimeout(() => setRefreshedToast(''), 3000);
  };

  const handleDeleteAllKnowledgeBase = async () => {
    const confirmed = window.confirm(
      "⚠️ PERMANENT DELETION WARNING:\n\nAre you sure you want to delete ALL uploaded PDF documents and all vector chunks from Supabase pgvector?\n\nThis will permanently purge the entire vector database and cannot be undone."
    );
    if (!confirmed) return;

    setDeletingAll(true);
    try {
      if (onDeleteAllDocs) {
        await onDeleteAllDocs();
      } else {
        const res = await fetch('/api/documents/all', { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete all documents');
      }
      setDeletedAllToast('All documents and vector chunks have been permanently deleted from Supabase.');
      setTimeout(() => setDeletedAllToast(''), 4000);
    } catch (err) {
      alert(`Error deleting documents: ${err.message}`);
    } finally {
      setDeletingAll(false);
    }
  };

  return (
    <div className="view-container settings-view">
      {/* Top Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title">System Settings & Configurations</h2>
          <p className="view-subtitle">
            Configure system parameters, review model statuses, and manage application data
          </p>
        </div>
      </div>

      {/* Notifications */}
      {clearedToast && (
        <div className="alert-message success">
          <CheckCircle2 size={16} />
          <span>{clearedToast}</span>
        </div>
      )}
      {refreshedToast && (
        <div className="alert-message success">
          <CheckCircle2 size={16} />
          <span>{refreshedToast}</span>
        </div>
      )}
      {deletedAllToast && (
        <div className="alert-message success">
          <CheckCircle2 size={16} />
          <span>{deletedAllToast}</span>
        </div>
      )}

      <div className="settings-sections-container">
        {/* Section 1: AI Models & LLM Configuration */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="flex-center-gap">
              <Cpu size={18} className="text-purple" />
              <h3 className="settings-card-title">Active AI Models & Provider</h3>
            </div>
            <span className="badge-online">Operational</span>
          </div>

          <div className="settings-grid">
            <div className="setting-item">
              <span className="setting-label">Chat Reasoning Model:</span>
              <span className="setting-value font-mono">gemini-3.6-flash</span>
              <span className="setting-hint">Official Google Gemini API</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Embeddings Model:</span>
              <span className="setting-value font-mono">gemini-embedding-001</span>
              <span className="setting-hint">Vector Dimension: 768 float</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Vector Database:</span>
              <span className="setting-value">Supabase PostgreSQL + pgvector</span>
              <span className="setting-hint">Table: 'documents' with HNSW indexing</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Default User Timezone:</span>
              <span className="setting-value font-mono">Asia/Karachi (UTC+5)</span>
              <span className="setting-hint">Resolves natural language dates</span>
            </div>
          </div>
        </div>

        {/* Section 2: RAG Ingestion & Chunking Parameters */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="flex-center-gap">
              <Sliders size={18} className="text-purple" />
              <h3 className="settings-card-title">RAG Pipeline Parameters</h3>
            </div>
          </div>

          <div className="settings-grid">
            <div className="setting-item">
              <span className="setting-label">Chunk Size:</span>
              <span className="setting-value">1,000 characters</span>
              <span className="setting-hint">Configured in backend .env</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Chunk Overlap:</span>
              <span className="setting-value">200 characters</span>
              <span className="setting-hint">Preserves semantic context across splits</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Top-K Chunks Retrieved:</span>
              <span className="setting-value">5 chunks</span>
              <span className="setting-hint">Supplied to LLM for answer synthesis</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Min Similarity Threshold:</span>
              <span className="setting-value">0.30 cosine similarity</span>
              <span className="setting-hint">Anti-hallucination cutoff</span>
            </div>
          </div>
        </div>

        {/* Section 3: Connected Services Status */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="flex-center-gap">
              <ShieldCheck size={18} className="text-purple" />
              <h3 className="settings-card-title">Connected Services & MCP Health</h3>
            </div>
          </div>

          <div className="services-status-list">
            <div className="service-status-row">
              <div className="flex-center-gap">
                <CheckCircle2 size={16} className="text-success" />
                <span className="service-name">Google Gemini GenAI SDK</span>
              </div>
              <span className="service-status-pill green">Connected</span>
            </div>

            <div className="service-status-row">
              <div className="flex-center-gap">
                <CheckCircle2 size={16} className="text-success" />
                <span className="service-name">Supabase PostgreSQL + pgvector</span>
              </div>
              <span className="service-status-pill green">Online ({documentsCount} documents)</span>
            </div>

            <div className="service-status-row">
              <div className="flex-center-gap">
                <CheckCircle2 size={16} className="text-success" />
                <span className="service-name">GitHub MCP Stdio Server</span>
              </div>
              <span className="service-status-pill green">Ready (@modelcontextprotocol/server-github)</span>
            </div>

            <div className="service-status-row">
              <div className="flex-center-gap">
                <CheckCircle2 size={16} className="text-success" />
                <span className="service-name">Google Calendar FastMCP Server</span>
              </div>
              <span className="service-status-pill green">Active (Conflict Detection Enabled)</span>
            </div>

            <div className="service-status-row">
              <div className="flex-center-gap">
                <CheckCircle2 size={16} className="text-success" />
                <span className="service-name">Email FastMCP Server & APScheduler</span>
              </div>
              <span className="service-status-pill green">Active (Persistent SQLite Store)</span>
            </div>
          </div>
        </div>

        {/* Section 4: Data Management & Actions */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="flex-center-gap">
              <Database size={18} className="text-purple" />
              <h3 className="settings-card-title">Data Management & Controls</h3>
            </div>
          </div>

          <div className="data-actions-row">
            <button 
              type="button" 
              className="btn-secondary-action"
              onClick={handleClearChatHistory}
            >
              <Trash2 size={15} />
              <span>Clear Chat History</span>
            </button>

            <button 
              type="button" 
              className="btn-secondary-action"
              onClick={handleRefreshKnowledgeBase}
            >
              <RotateCw size={15} />
              <span>Refresh Knowledge Base</span>
            </button>
          </div>

          {/* Danger Zone: Purge Knowledge Base */}
          <div className="danger-zone-box">
            <div className="danger-zone-info">
              <div className="flex-center-gap">
                <AlertTriangle size={16} className="text-danger" />
                <span className="danger-zone-title">Purge Vector Knowledge Base</span>
              </div>
              <p className="danger-zone-desc">
                Permanently delete all {documentsCount} uploaded PDF documents and their 768-dimensional vector chunks from Supabase PostgreSQL + pgvector. This action cannot be undone.
              </p>
            </div>
            
            <button 
              type="button" 
              className="btn-purge-danger"
              onClick={handleDeleteAllKnowledgeBase}
              disabled={deletingAll || documentsCount === 0}
              title={documentsCount === 0 ? "No documents stored in Supabase" : "Delete all documents and chunks"}
            >
              {deletingAll ? (
                <>
                  <Loader2 size={15} className="spin-icon" />
                  <span>Purging Supabase pgvector...</span>
                </>
              ) : (
                <>
                  <Trash2 size={15} />
                  <span>Delete All Chunks & Documents</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Section 5: Student & Assignment Information */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="flex-center-gap">
              <User size={18} className="text-purple" />
              <h3 className="settings-card-title">Student & Assignment Details</h3>
            </div>
          </div>

          <div className="settings-grid">
            <div className="setting-item">
              <span className="setting-label">Student Name:</span>
              <span className="setting-value font-semibold">Muhammad Hassaan</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Institution:</span>
              <span className="setting-value">Saylani Mass IT Training (SMIT)</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Course:</span>
              <span className="setting-value">Agentic AI & Multi-Agent Systems</span>
            </div>

            <div className="setting-item">
              <span className="setting-label">Architecture:</span>
              <span className="setting-value">LangGraph Supervisor + MCP + pgvector</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
