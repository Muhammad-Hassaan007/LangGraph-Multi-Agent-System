import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Database, 
  GitBranch, 
  Calendar, 
  Mail, 
  ShieldCheck, 
  MessageSquare, 
  Clock, 
  Trash2, 
  CheckCircle2, 
  Loader2,
  Cpu,
  Layers
} from 'lucide-react';

export default function AgentsView({ onStartChat }) {
  const [scheduledJobs, setScheduledJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [cancellingJobId, setCancellingJobId] = useState(null);

  const fetchScheduledJobs = async () => {
    setLoadingJobs(true);
    try {
      const res = await fetch('/api/scheduled-emails');
      if (res.ok) {
        const data = await res.json();
        setScheduledJobs(data.scheduled_emails || []);
      }
    } catch (err) {
      console.error('Failed to load scheduled jobs:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  useEffect(() => {
    fetchScheduledJobs();
  }, []);

  const handleCancelJob = async (jobId) => {
    setCancellingJobId(jobId);
    try {
      const res = await fetch(`/api/scheduled-emails/${jobId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setScheduledJobs((prev) => prev.filter((j) => (j.id || j.job_id) !== jobId));
      }
    } catch (err) {
      console.error('Failed to cancel job:', err);
    } finally {
      setCancellingJobId(null);
    }
  };

  const agentCards = [
    {
      id: 'supervisor',
      name: 'LangGraph Supervisor Agent',
      type: 'Core Orchestrator',
      icon: Sparkles,
      color: 'purple',
      status: 'Active (Online)',
      description: 'Coordinates and routes user requests dynamically to the appropriate specialized sub-agent. Maintains multi-turn conversation memory and handles sequential chaining.',
      capabilities: [
        'Natural Language Intent Classification',
        'Multi-Agent Routing & Sequential Chaining',
        'Conversation History & State Management',
        'Direct Conversational Responses'
      ],
      transport: 'LangGraph StateGraph Engine'
    },
    {
      id: 'rag',
      name: 'RAG Sub-Agent (Supabase pgvector)',
      type: 'Hosted Vector Store',
      icon: Database,
      color: 'blue',
      status: 'Active (Online)',
      description: 'Performs semantic similarity search over hosted Supabase PostgreSQL + pgvector. Strictly isolates documents and returns answers with exact page citations and zero hallucination.',
      capabilities: [
        'Page-by-page text extraction (pypdf)',
        'Google Gemini gemini-embedding-001 (768 dimensions)',
        'Supabase match_documents RPC with HNSW indexing',
        'Strict document_id isolation & page citations'
      ],
      transport: 'Supabase PostgreSQL + pgvector'
    },
    {
      id: 'github',
      name: 'GitHub MCP Sub-Agent',
      type: 'Official Stdio MCP',
      icon: GitBranch,
      color: 'violet',
      status: 'Active (Online)',
      description: 'Interacts with GitHub over real Model Context Protocol (MCP) stdio connection. Inspects repository structures, commits, open issues, PRs, and reads file contents.',
      capabilities: [
        'Official @modelcontextprotocol/server-github',
        'Read repository details & commits',
        'Inspect file contents (e.g. README.md)',
        'Human-in-the-Loop confirmation on write operations'
      ],
      transport: 'Real Stdio MCP (Node.js)'
    },
    {
      id: 'calendar',
      name: 'Google Calendar MCP Sub-Agent',
      type: 'FastMCP Stdio Server',
      icon: Calendar,
      color: 'cyan',
      status: 'Active (Online)',
      description: 'Manages calendar events and meetings. Resolves natural language dates (e.g. "tomorrow at 3pm") with user timezone and alerts on scheduling conflicts.',
      capabilities: [
        'FastMCP stdio server (mcp_tools/calendar_server.py)',
        'Natural language date resolution (Asia/Karachi)',
        'Conflict Detection before booking appointments',
        'Google OAuth 2.0 & fallback local JSON store'
      ],
      transport: 'FastMCP stdio (Python)'
    },
    {
      id: 'email',
      name: 'Email MCP Sub-Agent',
      type: 'FastMCP + APScheduler',
      icon: Mail,
      color: 'rose',
      status: 'Active (Online)',
      description: 'Drafts and sends emails with Human-in-the-Loop user confirmation cards. Features persistent future email scheduling backed by an SQLite job database.',
      capabilities: [
        'FastMCP stdio server (mcp_tools/email_server.py)',
        'Human-in-the-Loop Confirmation Card interceptor',
        'Persistent email scheduling via APScheduler',
        'SQLite job store (scheduled_emails.db)'
      ],
      transport: 'FastMCP stdio (Python) + SQLite'
    }
  ];

  return (
    <div className="view-container agents-view">
      {/* Top Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title">Active Multi-Agent System</h2>
          <p className="view-subtitle">
            All 5 specialized sub-agents and supervisors running in this system
          </p>
        </div>

        <button className="btn-primary-action" onClick={onStartChat}>
          <MessageSquare size={16} />
          <span>Start Chatting</span>
        </button>
      </div>

      {/* Agents Grid */}
      <div className="agents-cards-grid">
        {agentCards.map((agent) => {
          const Icon = agent.icon;
          return (
            <div key={agent.id} className="agent-detail-card">
              <div className="agent-card-header">
                <div className={`agent-avatar-wrap ${agent.color}`}>
                  <Icon size={20} />
                </div>
                <div className="agent-header-info">
                  <div className="agent-title-row">
                    <h3 className="agent-card-name">{agent.name}</h3>
                    <span className="agent-type-pill">{agent.type}</span>
                  </div>
                  <div className="agent-status-badge-row">
                    <span className="live-agent-dot" />
                    <span className="agent-status-text">{agent.status}</span>
                  </div>
                </div>
              </div>

              <p className="agent-card-description">{agent.description}</p>

              <div className="agent-card-capabilities">
                <span className="cap-label">Key Capabilities:</span>
                <ul>
                  {agent.capabilities.map((cap, i) => (
                    <li key={i}>
                      <CheckCircle2 size={12} className="text-success" />
                      <span>{cap}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="agent-card-footer">
                <span className="transport-label">Protocol / Store:</span>
                <span className="transport-badge">{agent.transport}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Persistent Scheduled Emails Queue */}
      <div className="scheduled-queue-section">
        <div className="queue-section-header">
          <div className="flex-center-gap">
            <Clock size={18} className="text-purple" />
            <h3 className="queue-title">Persistent Email Scheduler Queue (APScheduler)</h3>
          </div>
          <button 
            type="button" 
            className="btn-refresh-queue" 
            onClick={fetchScheduledJobs}
            disabled={loadingJobs}
          >
            {loadingJobs ? <Loader2 size={13} className="spin-icon" /> : 'Refresh Queue'}
          </button>
        </div>

        {scheduledJobs.length === 0 ? (
          <div className="queue-empty-box">
            <CheckCircle2 size={18} className="text-success" />
            <span>No pending scheduled emails. Ask the assistant: "Schedule an email to user@example.com tomorrow at 10am"</span>
          </div>
        ) : (
          <div className="queue-jobs-list">
            {scheduledJobs.map((job) => {
              const jobId = job.id || job.job_id || 'unknown';
              const runAt = job.next_run_time || job.run_at;
              return (
                <div key={jobId} className="queue-job-row">
                  <div className="job-info">
                    <span className="job-name">{job.name || job.subject || 'Scheduled Email'}</span>
                    <span className="job-time">
                      <Clock size={11} />
                      {runAt ? new Date(runAt).toLocaleString() : 'Scheduled'}
                    </span>
                  </div>
                  <div className="job-actions">
                    <span className="job-id-pill">ID: {jobId}</span>
                    <button
                      type="button"
                      className="btn-cancel-job-small"
                      disabled={cancellingJobId === jobId}
                      onClick={() => handleCancelJob(jobId)}
                      title="Cancel Job"
                    >
                      {cancellingJobId === jobId ? (
                        <Loader2 size={13} className="spin-icon" />
                      ) : (
                        <Trash2 size={13} />
                      )}
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
