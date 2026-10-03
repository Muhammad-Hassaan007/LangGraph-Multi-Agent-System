import React, { useState } from 'react';
import { 
  GitBranch, 
  Search, 
  Terminal, 
  BookOpen, 
  Code, 
  GitCommit, 
  AlertCircle, 
  MessageSquare, 
  CheckCircle2, 
  Loader2, 
  Copy, 
  ExternalLink,
  Sparkles,
  ArrowRight
} from 'lucide-react';

export default function GitHubView({ 
  onSendToChat, 
  onStartNewChatWithGitHub, 
  onSwitchToChat 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('repositories'); // 'repositories' | 'code' | 'commits' | 'issues' | 'all'
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [recentSearches, setRecentSearches] = useState([
    { query: 'octocat/Hello-World README', type: 'code' },
    { query: 'langchain-ai/langgraph', type: 'repositories' },
    { query: 'FastAPI router examples', type: 'code' },
  ]);

  const searchCategories = [
    { id: 'repositories', label: 'Repositories', icon: BookOpen },
    { id: 'code', label: 'Code & Files', icon: Code },
    { id: 'commits', label: 'Commits', icon: GitCommit },
    { id: 'issues', label: 'Issues & PRs', icon: AlertCircle },
    { id: 'all', label: 'General / All', icon: GitBranch },
  ];

  const handleSearch = async (queryToSearch = searchQuery, typeToSearch = searchType) => {
    const q = (queryToSearch || '').trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setResult(null);

    // Add to recent searches if not already present
    if (!recentSearches.some((s) => s.query.toLowerCase() === q.toLowerCase())) {
      setRecentSearches((prev) => [{ query: q, type: typeToSearch }, ...prev.slice(0, 5)]);
    }

    try {
      const res = await fetch('/api/github/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          search_type: typeToSearch,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'GitHub search failed');
      }

      setResult(data);
    } catch (err) {
      console.error('GitHub search error:', err);
      setError(err.message || 'Failed to communicate with GitHub MCP server.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleCopyResult = () => {
    if (!result?.answer) return;
    navigator.clipboard.writeText(result.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Create a brand new chat session for this GitHub question (not in the previous one)
  const handleOpenInNewChat = () => {
    if (!result?.answer) return;
    const prompt = `Search GitHub for: "${searchQuery}"`;
    if (onStartNewChatWithGitHub) {
      onStartNewChatWithGitHub(prompt, result.answer);
    } else {
      if (onSendToChat) onSendToChat(prompt);
      if (onSwitchToChat) onSwitchToChat();
    }
  };

  return (
    <div className="view-container github-view">
      {/* Top Header */}
      <div className="view-header">
        <div>
          <div className="flex-center-gap">
            <h2 className="view-title">GitHub MCP Explorer & Search</h2>
            <span className="badge-mcp-online">Real Stdio MCP</span>
          </div>
          <p className="view-subtitle">
            Search public repositories, inspect code and file contents, view commits, and track issues via the official GitHub Model Context Protocol server
          </p>
        </div>

        <button 
          className="btn-primary-action"
          onClick={() => {
            if (onSwitchToChat) onSwitchToChat();
          }}
        >
          <MessageSquare size={16} />
          <span>Switch to Chat</span>
        </button>
      </div>

      {/* Category Filter Pills */}
      <div className="github-category-tabs">
        {searchCategories.map((cat) => {
          const Icon = cat.icon;
          const isActive = searchType === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              className={`cat-pill-btn ${isActive ? 'active' : ''}`}
              onClick={() => setSearchType(cat.id)}
            >
              <Icon size={14} />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Large Search Input Bar */}
      <div className="github-search-box">
        <div className="github-input-wrap">
          <Search size={18} className="search-icon-purple" />
          <input
            type="text"
            className="github-main-input"
            placeholder={
              searchType === 'repositories'
                ? "Search repositories (e.g. langchain-ai/langgraph, react, fastmcp)..."
                : searchType === 'code'
                ? "Search code or file path (e.g. README in octocat/Hello-World)..."
                : searchType === 'commits'
                ? "List commits (e.g. octocat/Hello-World latest commits)..."
                : searchType === 'issues'
                ? "Search issues or PRs (e.g. open issues in octocat/Hello-World)..."
                : "Search anything across GitHub via MCP..."
            }
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        <button 
          type="button"
          className="btn-search-github"
          onClick={() => handleSearch()}
          disabled={loading || !searchQuery.trim()}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="spin-icon" />
              <span>Searching MCP...</span>
            </>
          ) : (
            <>
              <Search size={16} />
              <span>Search GitHub</span>
            </>
          )}
        </button>
      </div>

      {/* Quick Suggestions / Recent Searches */}
      <div className="github-suggestions-row">
        <span className="suggestion-label">Quick Suggestions:</span>
        <div className="suggestion-chips">
          <button 
            type="button" 
            className="suggestion-chip"
            onClick={() => {
              setSearchQuery('octocat/Hello-World README');
              setSearchType('code');
              handleSearch('octocat/Hello-World README', 'code');
            }}
          >
            octocat/Hello-World README
          </button>

          <button 
            type="button" 
            className="suggestion-chip"
            onClick={() => {
              setSearchQuery('langchain-ai/langgraph');
              setSearchType('repositories');
              handleSearch('langchain-ai/langgraph', 'repositories');
            }}
          >
            langchain-ai/langgraph
          </button>

          <button 
            type="button" 
            className="suggestion-chip"
            onClick={() => {
              setSearchQuery('FastAPI router examples');
              setSearchType('code');
              handleSearch('FastAPI router examples', 'code');
            }}
          >
            FastAPI router examples
          </button>

          <button 
            type="button" 
            className="suggestion-chip"
            onClick={() => {
              setSearchQuery('octocat/Hello-World latest commits');
              setSearchType('commits');
              handleSearch('octocat/Hello-World latest commits', 'commits');
            }}
          >
            octocat/Hello-World commits
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="alert-message error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Search Result Card */}
      {result && (
        <div className="github-result-card">
          <div className="result-card-header">
            <div className="flex-center-gap">
              <CheckCircle2 size={18} className="text-success" />
              <h3 className="result-card-title">GitHub MCP Response</h3>
              {result.tool_used && (
                <span className="tool-used-badge">Tool: {result.tool_used}</span>
              )}
            </div>

            <div className="result-header-actions">
              <button 
                type="button" 
                className="btn-action-ghost"
                onClick={handleCopyResult}
                title="Copy markdown answer"
              >
                <Copy size={14} />
                <span>{copied ? 'Copied!' : 'Copy'}</span>
              </button>

              <button 
                type="button" 
                className="btn-action-primary"
                onClick={handleOpenInNewChat}
                title="Create a new chat conversation with this GitHub question and result"
              >
                <MessageSquare size={14} />
                <span>Open in New Chat</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>

          <div className="result-card-body">
            <div className="result-markdown-content">
              {result.answer}
            </div>
          </div>

          <div className="result-card-footer">
            <div className="flex-center-gap">
              <Terminal size={14} className="text-muted" />
              <span className="footer-meta-text">
                Query executed via Node.js Stdio MCP (@modelcontextprotocol/server-github)
              </span>
            </div>
            <span className="footer-category-pill">Category: {result.search_type || searchType}</span>
          </div>
        </div>
      )}

      {/* Default / Explanatory State */}
      {!result && !loading && (
        <div className="github-overview-grid">
          <div className="overview-card">
            <div className="overview-icon-wrap violet">
              <BookOpen size={20} />
            </div>
            <h4>Repository Search</h4>
            <p>Inspect public and private repositories, star counts, descriptions, topics, and owner details.</p>
          </div>

          <div className="overview-card">
            <div className="overview-icon-wrap blue">
              <Code size={20} />
            </div>
            <h4>Code & File Contents</h4>
            <p>Read repository files, examine project READMEs, and search source code across GitHub.</p>
          </div>

          <div className="overview-card">
            <div className="overview-icon-wrap purple">
              <GitCommit size={20} />
            </div>
            <h4>Commits & History</h4>
            <p>Fetch commit histories, commit messages, authors, timestamps, and commit shas.</p>
          </div>

          <div className="overview-card">
            <div className="overview-icon-wrap cyan">
              <AlertCircle size={20} />
            </div>
            <h4>Issues & Pull Requests</h4>
            <p>List open and closed issues, read pull request reviews, and track discussions safely.</p>
          </div>
        </div>
      )}
    </div>
  );
}
