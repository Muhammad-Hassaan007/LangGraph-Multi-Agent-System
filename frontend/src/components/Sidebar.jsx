import React, { useState } from 'react';
import { 
  FileText, 
  Search, 
  Plus, 
  Trash2, 
  RotateCw, 
  Clock, 
  UploadCloud,
  GitBranch,
  BookOpen,
  Code,
  GitCommit,
  AlertCircle,
  Loader2,
  MessageSquare,
  ArrowRight
} from 'lucide-react';

export default function Sidebar({
  documents,
  selectedDocId,
  onSelectDoc,
  onDeleteDoc,
  onOpenUploadModal,
  onRefreshDocs,
  onSendPromptToChat,
  onStartNewChatWithGitHub,
}) {
  const [activeSection, setActiveSection] = useState('documents'); // 'documents' | 'github'
  const [searchTerm, setSearchTerm] = useState('');

  // GitHub Search State
  const [githubQuery, setGithubQuery] = useState('');
  const [githubType, setGithubType] = useState('repositories'); // 'repositories' | 'code' | 'commits' | 'issues'
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubResult, setGithubResult] = useState(null);
  const [githubError, setGithubError] = useState(null);

  // Filter documents by user search query
  const filteredDocs = documents.filter((doc) =>
    (doc.filename || '').toLowerCase().includes(searchTerm.toLowerCase().trim())
  );

  // Format date helper: "Aug 28, 2026"
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

  const handleGitHubSearch = async (overrideQuery = githubQuery, overrideType = githubType) => {
    const q = (overrideQuery || '').trim();
    if (!q) return;

    setGithubLoading(true);
    setGithubError(null);
    setGithubResult(null);

    try {
      const res = await fetch('/api/github/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          search_type: overrideType,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'GitHub search failed');
      }

      setGithubResult(data);
    } catch (err) {
      console.error('Sidebar GitHub search error:', err);
      setGithubError(err.message || 'Search failed');
    } finally {
      setGithubLoading(false);
    }
  };

  const handleSendToChat = () => {
    if (!githubResult?.answer) return;
    const prompt = `Search GitHub for: "${githubQuery}"`;
    if (onStartNewChatWithGitHub) {
      onStartNewChatWithGitHub(prompt, githubResult.answer);
    } else if (onSendPromptToChat) {
      onSendPromptToChat(prompt);
    }
  };

  return (
    <div className="knowledge-panel">
      {/* Top Section Segmented Control Switcher */}
      <div className="sidebar-section-switcher">
        <button
          type="button"
          className={`switcher-tab-btn ${activeSection === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveSection('documents')}
        >
          <FileText size={13} />
          <span>Documents ({documents.length})</span>
        </button>

        <button
          type="button"
          className={`switcher-tab-btn ${activeSection === 'github' ? 'active' : ''}`}
          onClick={() => setActiveSection('github')}
        >
          <GitBranch size={13} />
          <span>GitHub Search</span>
        </button>
      </div>

      {/* SECTION 1: KNOWLEDGE DOCUMENTS */}
      {activeSection === 'documents' && (
        <>
          {/* Panel Header */}
          <div className="knowledge-header">
            <div className="knowledge-title-wrap">
              <h2 className="knowledge-title">Knowledge Documents</h2>
            </div>

            <div className="knowledge-actions">
              {onRefreshDocs && (
                <button 
                  className="btn-icon-refresh" 
                  onClick={onRefreshDocs}
                  title="Refresh document list"
                >
                  <RotateCw size={14} />
                </button>
              )}

              <button 
                className="btn-upload-purple" 
                onClick={onOpenUploadModal}
                title="Upload new PDF document into Supabase"
              >
                <Plus size={15} />
                <span>Upload PDF</span>
              </button>
            </div>
          </div>

          {/* Search Input Bar */}
          <div className="knowledge-search-bar">
            <Search size={15} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Document List */}
          <div className="doc-cards-list">
            {filteredDocs.length === 0 ? (
              <div className="empty-docs-state">
                <div className="empty-docs-icon-wrap">
                  <UploadCloud size={24} />
                </div>
                <p className="empty-docs-title">
                  {searchTerm ? 'No matching documents' : 'No documents indexed'}
                </p>
                <p className="empty-docs-desc">
                  {searchTerm
                    ? 'Try a different search keyword'
                    : 'Upload a PDF to store in Supabase pgvector'}
                </p>
                <button className="btn-upload-link" onClick={onOpenUploadModal}>
                  + Upload PDF
                </button>
              </div>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = doc.document_id === selectedDocId;
                return (
                  <div
                    key={doc.document_id}
                    className={`doc-card-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => onSelectDoc(doc.document_id)}
                  >
                    {/* Red PDF Icon badge */}
                    <div className="pdf-icon-badge">
                      <FileText size={16} />
                    </div>

                    {/* Doc Details */}
                    <div className="doc-card-details">
                      <span className="doc-card-title" title={doc.filename}>
                        {doc.filename}
                      </span>
                      <div className="doc-card-meta">
                        <span>
                          {doc.total_pages || 1} {doc.total_pages === 1 ? 'page' : 'pages'} • {doc.chunks_count || 0} chunks
                        </span>
                      </div>
                      <div className="doc-card-date">
                        <Clock size={11} />
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                    </div>

                    {/* Active Indicator or Actions */}
                    <div className="doc-card-actions">
                      {isSelected && (
                        <span className="purple-active-dot" title="Active Context" />
                      )}
                      <button
                        type="button"
                        className="btn-trash-doc"
                        title={`Delete ${doc.filename}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Delete "${doc.filename}" from Supabase?`)) {
                            onDeleteDoc(doc.document_id);
                          }
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}

      {/* SECTION 2: GITHUB SEARCH PANEL */}
      {activeSection === 'github' && (
        <div className="sidebar-github-panel">
          <div className="sidebar-github-header">
            <h3 className="sidebar-github-title">Search GitHub</h3>
            <span className="mcp-badge-tiny">MCP Stdio</span>
          </div>

          {/* Filter Pills */}
          <div className="sidebar-github-types">
            <button
              type="button"
              className={`pill-mini ${githubType === 'repositories' ? 'active' : ''}`}
              onClick={() => setGithubType('repositories')}
            >
              Repos
            </button>
            <button
              type="button"
              className={`pill-mini ${githubType === 'code' ? 'active' : ''}`}
              onClick={() => setGithubType('code')}
            >
              Code
            </button>
            <button
              type="button"
              className={`pill-mini ${githubType === 'commits' ? 'active' : ''}`}
              onClick={() => setGithubType('commits')}
            >
              Commits
            </button>
            <button
              type="button"
              className={`pill-mini ${githubType === 'issues' ? 'active' : ''}`}
              onClick={() => setGithubType('issues')}
            >
              Issues
            </button>
          </div>

          {/* Search Input Box */}
          <div className="sidebar-github-input-box">
            <div className="input-wrap-mini">
              <Search size={14} className="search-icon" />
              <input
                type="text"
                className="github-mini-input"
                placeholder={
                  githubType === 'repositories'
                    ? 'e.g. octocat/Hello-World'
                    : githubType === 'code'
                    ? 'e.g. README in octocat/Hello-World'
                    : githubType === 'commits'
                    ? 'e.g. latest commits octocat'
                    : 'e.g. open issues fastapi'
                }
                value={githubQuery}
                onChange={(e) => setGithubQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleGitHubSearch();
                }}
              />
            </div>
            <button
              type="button"
              className="btn-search-mini"
              onClick={() => handleGitHubSearch()}
              disabled={githubLoading || !githubQuery.trim()}
            >
              {githubLoading ? <Loader2 size={13} className="spin-icon" /> : 'Search'}
            </button>
          </div>

          {/* Quick Suggestions */}
          <div className="sidebar-github-chips">
            <span className="chips-title">Quick Queries:</span>
            <div className="chips-row">
              <button
                type="button"
                className="chip-item"
                onClick={() => {
                  setGithubQuery('octocat/Hello-World README');
                  setGithubType('code');
                  handleGitHubSearch('octocat/Hello-World README', 'code');
                }}
              >
                octocat README
              </button>
              <button
                type="button"
                className="chip-item"
                onClick={() => {
                  setGithubQuery('langchain-ai/langgraph');
                  setGithubType('repositories');
                  handleGitHubSearch('langchain-ai/langgraph', 'repositories');
                }}
              >
                langgraph repo
              </button>
              <button
                type="button"
                className="chip-item"
                onClick={() => {
                  setGithubQuery('octocat commits');
                  setGithubType('commits');
                  handleGitHubSearch('octocat commits', 'commits');
                }}
              >
                octocat commits
              </button>
            </div>
          </div>

          {/* Error */}
          {githubError && (
            <div className="sidebar-github-error">
              <AlertCircle size={14} />
              <span>{githubError}</span>
            </div>
          )}

          {/* Result Snippet */}
          {githubResult && (
            <div className="sidebar-github-result">
              <div className="result-top-row">
                <span className="result-label">Result ({githubResult.tool_used || 'Answer'}):</span>
                {(onStartNewChatWithGitHub || onSendPromptToChat) && (
                  <button
                    type="button"
                    className="btn-send-to-chat"
                    onClick={handleSendToChat}
                    title="Start a new chat conversation with this GitHub question and result"
                  >
                    <span>Ask in New Chat</span>
                    <ArrowRight size={11} />
                  </button>
                )}
              </div>
              <div className="result-snippet-text">
                {githubResult.answer}
              </div>
            </div>
          )}

          {/* Empty hint */}
          {!githubResult && !githubLoading && (
            <div className="sidebar-github-hint-card">
              <GitBranch size={20} className="text-purple" />
              <p>Type any query above to search repositories, code files, and commits via the official GitHub MCP server.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
