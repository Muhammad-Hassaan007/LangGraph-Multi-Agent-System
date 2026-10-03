import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  FileText, 
  Loader2, 
  Sparkles, 
  HelpCircle, 
  UploadCloud,
  ChevronDown,
  Paperclip,
  GitBranch,
  Calendar,
  Mail
} from 'lucide-react';
import ChatMessage from './ChatMessage';

export default function ChatWindow({
  activeDoc,
  messages,
  loading,
  onSendMessage,
  onOpenUploadModal,
  onDirectUploadFile,
  onConfirmAction,
  onCancelAction,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [activeDoc]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handlePaperclipClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (onDirectUploadFile) {
        onDirectUploadFile(file);
      } else if (onOpenUploadModal) {
        onOpenUploadModal();
      }
      e.target.value = '';
    }
  };

  // Quick prompt buttons
  const quickQuestionsDoc = [
    "What is the main summary of this document?",
    "What are the key concepts and topics discussed?",
    "List the major conclusions or takeaways."
  ];

  const quickSuggestionsGeneral = [
    { text: "List my recent GitHub repositories", icon: GitBranch },
    { text: "What events are on my calendar today or tomorrow?", icon: Calendar },
    { text: "Write a draft email to team about project status", icon: Mail },
  ];

  // Determine active agent label in the top header
  const getActiveAgentLabel = () => {
    if (messages.length > 0) {
      const lastBotMsg = [...messages].reverse().find(m => m.role === 'assistant');
      if (lastBotMsg?.sender === 'github_agent') return 'GitHub MCP';
      if (lastBotMsg?.sender === 'calendar_agent') return 'Calendar MCP';
      if (lastBotMsg?.sender === 'email_agent') return 'Email MCP';
      if (lastBotMsg?.sender === 'rag_agent') return 'RAG Agent';
      if (lastBotMsg?.sender === 'supervisor') return 'Supervisor';
    }
    return activeDoc ? 'RAG Agent' : 'Multi-Agent';
  };

  return (
    <div className="chat-window">
      {/* Hidden file input for attachment button */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* Top Header */}
      <header className="chat-header">
        <div className="header-left">
          {activeDoc ? (
            <div className="header-doc-wrap">
              <div className="pdf-icon-badge small">
                <FileText size={15} />
              </div>
              <div className="header-doc-info">
                <div className="header-doc-title-row">
                  <span className="header-doc-title">{activeDoc.filename}</span>
                  <ChevronDown size={14} className="header-doc-chevron" />
                </div>
                <span className="header-doc-meta">
                  {activeDoc.total_pages || 1} {activeDoc.total_pages === 1 ? 'page' : 'pages'} • {activeDoc.chunks_count || 0} chunks
                </span>
              </div>
            </div>
          ) : (
            <div className="header-no-doc">
              <span className="header-no-doc-title">Universal Multi-Agent Mode</span>
              <span className="header-no-doc-sub">Select or upload a PDF for document RAG</span>
            </div>
          )}
        </div>

        <div className="header-right">
          <div className="live-agent-pill">
            <span className="live-agent-dot" />
            <span className="live-agent-name">{getActiveAgentLabel()}</span>
          </div>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="chat-messages-scroll">
        {messages.length === 0 ? (
          activeDoc ? (
            <div className="empty-state">
              <div className="pdf-icon-badge large">
                <FileText size={28} />
              </div>
              <h3 className="empty-state-title">Ready to Chat with {activeDoc.filename}</h3>
              <p className="empty-state-desc">
                The RAG Agent will search Supabase pgvector and cite exact pages with excerpts.
              </p>

              <div className="quick-questions-grid">
                {quickQuestionsDoc.map((q, idx) => (
                  <button
                    key={idx}
                    className="quick-q-btn"
                    onClick={() => onSendMessage(q)}
                  >
                    <HelpCircle size={14} />
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">
                <Sparkles size={36} className="text-purple" />
              </div>
              <h3 className="empty-state-title">Agentic AI Multi-Agent System</h3>
              <p className="empty-state-desc">
                Ask about <strong>GitHub</strong> repositories, schedule <strong>Google Calendar</strong> meetings, compose <strong>Emails</strong>, or attach a <strong>PDF</strong> for Supabase RAG.
              </p>

              <button className="btn-primary-action" onClick={onOpenUploadModal} style={{ marginBottom: '1.25rem' }}>
                <UploadCloud size={16} />
                <span>Upload PDF Document</span>
              </button>

              <div className="quick-questions-grid">
                {quickSuggestionsGeneral.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={idx}
                      className="quick-q-btn"
                      onClick={() => onSendMessage(item.text)}
                    >
                      <Icon size={14} className="text-purple" />
                      <span>{item.text}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )
        ) : (
          <div className="messages-list">
            {messages.map((msg, index) => (
              <ChatMessage 
                key={index} 
                message={msg} 
                onConfirmAction={onConfirmAction}
                onCancelAction={onCancelAction}
              />
            ))}

            {loading && (
              <div className="message-row bot-row">
                <div className="message-avatar ai-avatar">
                  <Sparkles size={16} />
                </div>
                <div className="message-content-wrapper">
                  <div className="message-bubble bot-bubble loading-bubble">
                    <Loader2 size={16} className="spin-icon" />
                    <span>Searching Supabase pgvector & synthesizing answer...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Footer Bar */}
      <footer className="chat-input-area">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          {/* Attachment Button */}
          <button
            type="button"
            className="btn-attachment"
            onClick={handlePaperclipClick}
            title="Attach or upload a PDF document"
          >
            <Paperclip size={18} />
          </button>

          {/* Text Area */}
          <textarea
            ref={inputRef}
            className="chat-textarea"
            placeholder={
              activeDoc
                ? `Ask about doc, a pdf, or ask GitHub, Calendar, Email... (Press Enter)`
                : `Ask about doc, a pdf, or ask GitHub, Calendar, Email... (Press Enter)`
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />

          {/* Send Button */}
          <button
            type="submit"
            className="btn-send-purple"
            disabled={!input.trim() || loading}
            title="Send Message"
          >
            {loading ? <Loader2 size={16} className="spin-icon" /> : <Send size={16} />}
          </button>
        </form>
      </footer>
    </div>
  );
}
