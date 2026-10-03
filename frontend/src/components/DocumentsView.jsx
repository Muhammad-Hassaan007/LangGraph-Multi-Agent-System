import React, { useState } from 'react';
import { 
  FileText, 
  Search, 
  Plus, 
  Trash2, 
  MessageSquare, 
  Database, 
  Layers, 
  Clock, 
  UploadCloud,
  CheckCircle2
} from 'lucide-react';

export default function DocumentsView({
  documents,
  selectedDocId,
  onSelectDocAndChat,
  onDeleteDoc,
  onOpenUploadModal,
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredDocs = documents.filter((doc) =>
    (doc.filename || '').toLowerCase().includes(searchTerm.toLowerCase().trim())
  );

  const totalPages = documents.reduce((acc, doc) => acc + (doc.total_pages || 1), 0);
  const totalChunks = documents.reduce((acc, doc) => acc + (doc.chunks_count || 0), 0);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Recent';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return 'Recent';
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return 'Recent';
    }
  };

  return (
    <div className="view-container documents-view">
      {/* Top Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title">Knowledge Documents Vault</h2>
          <p className="view-subtitle">
            All stored PDF documents indexed into Supabase PostgreSQL + pgvector
          </p>
        </div>

        <button className="btn-primary-action" onClick={onOpenUploadModal}>
          <Plus size={16} />
          <span>Upload New PDF</span>
        </button>
      </div>

      {/* Summary Stats Cards */}
      <div className="stats-cards-grid">
        <div className="stat-card">
          <div className="stat-icon-wrap purple">
            <FileText size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{documents.length}</span>
            <span className="stat-label">Stored Documents</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap indigo">
            <Layers size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{totalChunks}</span>
            <span className="stat-label">Total Chunks (pgvector)</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap emerald">
            <Database size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{totalPages}</span>
            <span className="stat-label">Indexed Pages</span>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="view-search-bar">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          className="search-input"
          placeholder="Search stored documents by name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <span className="search-count-hint">
          Showing {filteredDocs.length} of {documents.length} documents
        </span>
      </div>

      {/* Documents Grid */}
      <div className="documents-vault-grid">
        {filteredDocs.length === 0 ? (
          <div className="vault-empty-state">
            <UploadCloud size={48} className="text-muted" />
            <h3>No Documents Found</h3>
            <p>
              {searchTerm 
                ? 'No documents match your search criteria.' 
                : 'Upload your first PDF document to index it in Supabase pgvector.'}
            </p>
            <button className="btn-upload-purple" onClick={onOpenUploadModal}>
              <Plus size={15} />
              <span>Upload Document</span>
            </button>
          </div>
        ) : (
          filteredDocs.map((doc) => {
            const isSelected = doc.document_id === selectedDocId;
            return (
              <div 
                key={doc.document_id} 
                className={`vault-doc-card ${isSelected ? 'active-vault-card' : ''}`}
              >
                <div className="vault-card-top">
                  <div className="pdf-icon-badge">
                    <FileText size={18} />
                  </div>
                  <div className="vault-card-status">
                    <CheckCircle2 size={13} className="text-success" />
                    <span>Vector Indexed</span>
                  </div>
                </div>

                <div className="vault-card-body">
                  <h4 className="vault-doc-name" title={doc.filename}>
                    {doc.filename}
                  </h4>
                  <div className="vault-doc-meta-row">
                    <span>{doc.total_pages || 1} {doc.total_pages === 1 ? 'page' : 'pages'}</span>
                    <span className="meta-sep">•</span>
                    <span>{doc.chunks_count || 0} chunks</span>
                  </div>
                  <div className="vault-doc-date">
                    <Clock size={12} />
                    <span>Uploaded on {formatDate(doc.created_at)}</span>
                  </div>
                </div>

                <div className="vault-card-actions">
                  <button
                    type="button"
                    className="btn-chat-with-doc"
                    onClick={() => onSelectDocAndChat(doc.document_id)}
                    title="Open in Chat"
                  >
                    <MessageSquare size={14} />
                    <span>Chat With Document</span>
                  </button>

                  <button
                    type="button"
                    className="btn-delete-vault-doc"
                    onClick={() => {
                      if (window.confirm(`Delete "${doc.filename}" from Supabase vector database?`)) {
                        onDeleteDoc(doc.document_id);
                      }
                    }}
                    title="Delete document"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
