import React from 'react';
import { 
  Sparkles, 
  MessageSquare, 
  FileText, 
  GitBranch,
  Users, 
  Settings, 
  ChevronDown, 
  User,
  Plus
} from 'lucide-react';

export default function NavSidebar({ 
  activeTab = 'chat', 
  onSelectTab, 
  onNewChat 
}) {
  return (
    <aside className="nav-sidebar">
      {/* Brand Header */}
      <div className="nav-brand">
        <div className="nav-brand-icon">
          <Sparkles size={20} />
        </div>
        <div className="nav-brand-text">
          <h1 className="nav-brand-title">Agentic AI</h1>
          <p className="nav-brand-subtitle">LangGraph Multi-Agent System</p>
        </div>
      </div>

      {/* Primary Action: New Chat */}
      <button 
        type="button"
        className="btn-nav-new-chat"
        onClick={() => {
          if (onSelectTab) onSelectTab('chat');
          if (onNewChat) onNewChat();
        }}
        title="Start a new chat conversation"
      >
        <Plus size={16} />
        <span>New Chat</span>
      </button>

      {/* Navigation Links */}
      <nav className="nav-menu">
        <button 
          className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => {
            if (onSelectTab) onSelectTab('chat');
          }}
          title="Active Chat"
        >
          <MessageSquare size={17} />
          <span>Chat</span>
        </button>

        <button 
          className={`nav-item ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => {
            if (onSelectTab) onSelectTab('documents');
          }}
          title="View All Stored Knowledge Documents"
        >
          <FileText size={17} />
          <span>Documents</span>
        </button>

        <button 
          className={`nav-item ${activeTab === 'github' ? 'active' : ''}`}
          onClick={() => {
            if (onSelectTab) onSelectTab('github');
          }}
          title="Search GitHub Repositories, Code & Commits"
        >
          <GitBranch size={17} />
          <span>GitHub</span>
        </button>

        <button 
          className={`nav-item ${activeTab === 'agents' ? 'active' : ''}`}
          onClick={() => {
            if (onSelectTab) onSelectTab('agents');
          }}
          title="Inspect Sub-Agents and Roles"
        >
          <Users size={17} />
          <span>Agents</span>
        </button>

        <button 
          className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => {
            if (onSelectTab) onSelectTab('settings');
          }}
          title="System Settings & Configurations"
        >
          <Settings size={17} />
          <span>Settings</span>
        </button>
      </nav>

      {/* Bottom Cards */}
      <div className="nav-footer">
        {/* System Status Card */}
        <div 
          className="system-status-card"
          onClick={() => {
            if (onSelectTab) onSelectTab('agents');
          }}
          title="Click to view agent architecture and status"
        >
          <div className="status-indicator-wrap">
            <span className="system-live-dot" />
          </div>
          <div className="status-card-info">
            <span className="status-card-title">System Online</span>
            <span className="status-card-desc">All agents are ready</span>
          </div>
          <ChevronDown size={15} className="status-card-chevron" />
        </div>

        {/* User Profile Card */}
        <div className="user-profile-card">
          <div className="user-avatar">
            <User size={16} />
          </div>
          <div className="user-profile-info">
            <span className="user-name">Muhammad Hassaan</span>
            <span className="user-role">Student • SMIT</span>
          </div>
          <ChevronDown size={15} className="user-profile-chevron" />
        </div>
      </div>
    </aside>
  );
}
