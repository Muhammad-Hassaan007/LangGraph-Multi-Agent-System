import React, { useState } from 'react';
import { 
  User, 
  Bot, 
  FileText, 
  ChevronDown, 
  ChevronUp, 
  Sparkles,
  GitBranch,
  Calendar,
  Mail,
  Database,
  ShieldAlert,
  Check,
  X
} from 'lucide-react';

export default function ChatMessage({ message, onConfirmAction, onCancelAction }) {
  const isUser = message.role === 'user';
  const [sourcesOpen, setSourcesOpen] = useState(false);

  // Formatted timestamp
  const getTimestamp = () => {
    if (message.timestamp) return message.timestamp;
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Render markdown-like text lines
  const renderFormattedText = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} className="spacer-xs" />;
      }

      // Headers / Bold key labels
      let content = line;
      // Handle bold **text**
      const parts = content.split(/(\*\*.*?\*\*)/g);
      const renderedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return (
          <div key={idx} className="bullet-item">
            <span className="bullet-dot">•</span>
            <span>{renderedParts}</span>
          </div>
        );
      }

      return <p key={idx} className="text-paragraph">{renderedParts}</p>;
    });
  };

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'bot-row'}`}>
      {/* Bot Avatar on Left */}
      {!isUser && (
        <div className="message-avatar ai-avatar">
          <Sparkles size={16} />
        </div>
      )}

      <div className="message-content-wrapper">
        <div className={`message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`}>
          <div className="message-text">
            {renderFormattedText(message.content)}
          </div>

          {/* Timestamp */}
          <div className="message-timestamp">
            {getTimestamp()}
          </div>

          {/* Human-In-The-Loop Confirmation Card */}
          {!isUser && message.pending_action && (
            <div className="confirmation-card">
              <div className="confirmation-card-header">
                <ShieldAlert size={16} className="text-warning" />
                <span className="confirmation-title">Action Confirmation Required</span>
              </div>
              <div className="confirmation-body">
                <div className="confirmation-row">
                  <span className="confirmation-label">Action:</span>
                  <span className="confirmation-value">{message.pending_action.action || message.pending_action.tool || 'Execute Tool'}</span>
                </div>
                {message.pending_action.args && Object.entries(message.pending_action.args).map(([key, val]) => (
                  <div key={key} className="confirmation-row">
                    <span className="confirmation-label">{key}:</span>
                    <span className="confirmation-value">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="confirmation-actions">
                <button
                  type="button"
                  className="btn-confirm-action"
                  onClick={() => onConfirmAction && onConfirmAction(message.pending_action)}
                >
                  <Check size={14} />
                  <span>Confirm & Proceed</span>
                </button>
                <button
                  type="button"
                  className="btn-cancel-action"
                  onClick={() => onCancelAction && onCancelAction(message)}
                >
                  <X size={14} />
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          )}

          {/* Sources & Citations Section */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="sources-container">
              <button
                className="sources-toggle-btn"
                onClick={() => setSourcesOpen(!sourcesOpen)}
              >
                <div className="flex-center-gap">
                  <FileText size={13} />
                  <span>
                    {message.sources.length} {message.sources.length === 1 ? 'Source Citation' : 'Source Citations'}
                  </span>
                </div>
                {sourcesOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {sourcesOpen && (
                <div className="sources-list">
                  {message.sources.map((src, i) => (
                    <div key={i} className="source-card">
                      <div className="source-card-header">
                        <span className="source-filename">{src.filename}</span>
                        <span className="source-badge">
                          Page {src.page ?? src.page_number}
                        </span>
                      </div>
                      <p className="source-excerpt">
                        "{src.content.length > 200 ? src.content.substring(0, 200) + '...' : src.content}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* User Avatar on Right */}
      {isUser && (
        <div className="message-avatar user-avatar">
          <User size={15} />
        </div>
      )}
    </div>
  );
}
