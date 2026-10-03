import React, { useState, useEffect } from 'react';
import NavSidebar from './components/NavSidebar';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import DocumentsView from './components/DocumentsView';
import GitHubView from './components/GitHubView';
import AgentsView from './components/AgentsView';
import SettingsView from './components/SettingsView';
import PDFUploader from './components/PDFUploader';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents' | 'github' | 'agents' | 'settings'
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  
  // Per-document persistent chat histories, initialized from localStorage
  const [chatHistories, setChatHistories] = useState(() => {
    try {
      const saved = localStorage.getItem('agentic_ai_chat_histories');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadToast, setUploadToast] = useState(null);

  // Active chat key: selectedDocId or 'general'
  const currentChatKey = selectedDocId || 'general';

  // Active messages to display for currently active document/session
  const messages = chatHistories[currentChatKey] || [];

  // Persist chatHistories to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('agentic_ai_chat_histories', JSON.stringify(chatHistories));
    } catch (err) {
      console.error('Failed to save chatHistories:', err);
    }
  }, [chatHistories]);

  // Fetch documents on initial load
  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
        if (data.length > 0 && !selectedDocId) {
          setSelectedDocId(data[0].document_id);
        }
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Active document object
  const activeDoc = documents.find((d) => d.document_id === selectedDocId) || null;

  // Handle selecting active document
  const handleSelectDoc = (docId) => {
    setSelectedDocId(docId);
  };

  // Handle selecting a document from DocumentsView and switching to Chat
  const handleSelectDocAndChat = (docId) => {
    setSelectedDocId(docId);
    setActiveTab('chat');
  };

  // Handle document deletion
  const handleDeleteDoc = async (docId) => {
    try {
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        const updated = documents.filter((d) => d.document_id !== docId);
        setDocuments(updated);
        setChatHistories((prev) => {
          const next = { ...prev };
          delete next[docId];
          return next;
        });
        if (selectedDocId === docId) {
          setSelectedDocId(updated.length > 0 ? updated[0].document_id : null);
        }
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  // Handle deleting all documents & vector chunks from Supabase
  const handleDeleteAllDocs = async () => {
    try {
      const res = await fetch('/api/documents/all', { method: 'DELETE' });
      if (res.ok) {
        setDocuments([]);
        setSelectedDocId(null);
        // Retain only general chat
        setChatHistories((prev) => ({ general: prev['general'] || [] }));
        return true;
      } else {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to delete all documents');
      }
    } catch (err) {
      console.error('Failed to delete all documents:', err);
      throw err;
    }
  };

  // Clear chat (New Chat for the current document/session)
  const handleNewChat = () => {
    setChatHistories((prev) => ({
      ...prev,
      [currentChatKey]: [],
    }));
  };

  // Successful upload callback from modal or direct attachment
  const handleUploadSuccess = (newDoc) => {
    setDocuments((prev) => [
      {
        document_id: newDoc.document_id,
        filename: newDoc.filename,
        total_pages: newDoc.total_pages,
        chunks_count: newDoc.chunks ?? newDoc.chunks_count ?? 0,
        created_at: new Date().toISOString(),
      },
      ...prev.filter((d) => d.document_id !== newDoc.document_id),
    ]);
    setSelectedDocId(newDoc.document_id);
    setActiveTab('chat');
    setUploadModalOpen(false);
  };

  // Direct upload handler from Paperclip attachment button
  const handleDirectUploadFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please select a valid PDF (.pdf) file.');
      return;
    }

    setUploadToast(`Indexing "${file.name}" into Supabase pgvector...`);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      handleUploadSuccess(data);
      setUploadToast(`Successfully indexed "${file.name}"!`);
      setTimeout(() => setUploadToast(null), 3500);
    } catch (err) {
      console.error('Direct upload error:', err);
      alert(`Error indexing PDF: ${err.message}`);
      setUploadToast(null);
    }
  };

  // Send message to Universal LangGraph Multi-Agent System (/api/agent)
  const handleSendMessage = async (userText, options = {}) => {
    const { confirmed = false, pending_action = null } = options;
    if (!userText.trim() && !confirmed) return;

    const chatKey = currentChatKey;
    const currentMsgs = chatHistories[chatKey] || [];

    const userMessage = {
      role: 'user',
      content: confirmed
        ? `Confirmed action: ${pending_action?.action || pending_action?.tool || 'Execute'}`
        : userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const updatedMessages = [...currentMsgs, userMessage];
    setChatHistories((prev) => ({
      ...prev,
      [chatKey]: updatedMessages,
    }));
    setLoading(true);

    try {
      const res = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText || (confirmed ? 'Confirmed' : ''),
          question: userText || (confirmed ? 'Confirmed' : ''),
          query: userText || (confirmed ? 'Confirmed' : ''),
          document_id: selectedDocId || null,
          confirmed: Boolean(confirmed),
          pending_action: pending_action,
          history: currentMsgs
            .filter((m) => m.role === 'user' || m.role === 'assistant')
            .slice(-8)
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to get answer from Multi-Agent System.');
      }

      const botMessage = {
        role: 'assistant',
        content: data.answer || '',
        sender: data.sender || (selectedDocId ? 'rag_agent' : 'supervisor'),
        sources: data.sources || [],
        pending_action: data.pending_action || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setChatHistories((prev) => ({
        ...prev,
        [chatKey]: [...(prev[chatKey] || []), botMessage],
      }));
    } catch (err) {
      console.error('Multi-Agent chat error:', err);
      const errorMessage = {
        role: 'assistant',
        content: `⚠️ Error: ${err.message}`,
        sender: selectedDocId ? 'rag_agent' : 'supervisor',
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatHistories((prev) => ({
        ...prev,
        [chatKey]: [...(prev[chatKey] || []), errorMessage],
      }));
    } finally {
      setLoading(false);
    }
  };

  // Handle starting a brand-new chat session for GitHub inquiries (not appending to previous chat)
  const handleStartNewChatWithGitHub = async (userPrompt, preloadedAnswer = null) => {
    // Deselect document so it operates in a clean general/github mode
    setSelectedDocId(null);
    const gitKey = 'general';
    setActiveTab('chat');

    const userMessage = {
      role: 'user',
      content: userPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    if (preloadedAnswer) {
      const assistantMessage = {
        role: 'assistant',
        content: preloadedAnswer,
        sender: 'github_agent',
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      // Brand new chat initialized with exclusively this GitHub inquiry & response
      setChatHistories((prev) => ({
        ...prev,
        [gitKey]: [userMessage, assistantMessage],
      }));
      return;
    }

    // Clear old messages and query fresh with empty history
    setChatHistories((prev) => ({
      ...prev,
      [gitKey]: [userMessage],
    }));
    setLoading(true);

    try {
      const res = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userPrompt,
          question: userPrompt,
          query: userPrompt,
          document_id: null,
          confirmed: false,
          history: [], // Fresh new thread without previous chat turns
        }),
      });

      const data = await responseData(res);
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to get answer from Multi-Agent System.');
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.answer || 'No response received.',
        sender: data.sender || 'github_agent',
        sources: data.sources || [],
        pending_action: data.pending_action || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setChatHistories((prev) => ({
        ...prev,
        [gitKey]: [userMessage, assistantMessage],
      }));
    } catch (err) {
      console.error('New GitHub chat error:', err);
      const errorMessage = {
        role: 'assistant',
        content: `❌ Error: ${err.message}`,
        sender: 'github_agent',
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatHistories((prev) => ({
        ...prev,
        [gitKey]: [userMessage, errorMessage],
      }));
    } finally {
      setLoading(false);
    }
  };

  // Human-in-the-Loop action confirmation
  const handleConfirmAction = (pendingAction) => {
    const chatKey = currentChatKey;
    setChatHistories((prev) => ({
      ...prev,
      [chatKey]: (prev[chatKey] || []).map((m) =>
        m.pending_action ? { ...m, pending_action: null } : m
      ),
    }));
    handleSendMessage('Confirmed', { confirmed: true, pending_action: pendingAction });
  };

  // Human-in-the-Loop action cancellation
  const handleCancelAction = (targetMessage) => {
    const chatKey = currentChatKey;
    const cancelNotice = {
      role: 'assistant',
      content: 'Action was cancelled by user.',
      sender: targetMessage?.sender || 'supervisor',
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setChatHistories((prev) => ({
      ...prev,
      [chatKey]: [
        ...(prev[chatKey] || []).map((m) =>
          m === targetMessage ? { ...m, pending_action: null } : m
        ),
        cancelNotice,
      ],
    }));
  };

  const responseData = async (res) => {
    try {
      return await res.json();
    } catch {
      return { detail: 'Unexpected response from server' };
    }
  };

  return (
    <div className="app-layout">
      {/* Toast Notification */}
      {uploadToast && (
        <div className="app-toast">
          <span>{uploadToast}</span>
        </div>
      )}

      {/* Main App Frame */}
      <div className="app-window-frame">
        {/* Column 1: Left Navigation Sidebar */}
        <NavSidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          onNewChat={handleNewChat}
        />

        {/* Content View Switching */}
        {activeTab === 'chat' && (
          <>
            {/* Column 2: Knowledge Documents Panel & Quick GitHub Search */}
            <Sidebar
              documents={documents}
              selectedDocId={selectedDocId}
              onSelectDoc={handleSelectDoc}
              onDeleteDoc={handleDeleteDoc}
              onOpenUploadModal={() => setUploadModalOpen(true)}
              onRefreshDocs={fetchDocuments}
              onSendPromptToChat={(text) => handleSendMessage(text)}
              onStartNewChatWithGitHub={handleStartNewChatWithGitHub}
            />

            {/* Column 3: Main Chat Window */}
            <main className="chat-main-area">
              <ChatWindow
                activeDoc={activeDoc}
                messages={messages}
                loading={loading}
                onSendMessage={(text) => handleSendMessage(text)}
                onOpenUploadModal={() => setUploadModalOpen(true)}
                onDirectUploadFile={handleDirectUploadFile}
                onConfirmAction={handleConfirmAction}
                onCancelAction={handleCancelAction}
              />
            </main>
          </>
        )}

        {activeTab === 'documents' && (
          <main className="tab-full-content-area">
            <DocumentsView
              documents={documents}
              selectedDocId={selectedDocId}
              onSelectDocAndChat={handleSelectDocAndChat}
              onDeleteDoc={handleDeleteDoc}
              onOpenUploadModal={() => setUploadModalOpen(true)}
            />
          </main>
        )}

        {activeTab === 'github' && (
          <main className="tab-full-content-area">
            <GitHubView
              onSendToChat={(prompt) => handleSendMessage(prompt)}
              onStartNewChatWithGitHub={handleStartNewChatWithGitHub}
              onSwitchToChat={() => setActiveTab('chat')}
            />
          </main>
        )}

        {activeTab === 'agents' && (
          <main className="tab-full-content-area">
            <AgentsView
              onStartChat={() => setActiveTab('chat')}
            />
          </main>
        )}

        {activeTab === 'settings' && (
          <main className="tab-full-content-area">
            <SettingsView
              onClearChat={handleNewChat}
              onRefreshDocs={fetchDocuments}
              onDeleteAllDocs={handleDeleteAllDocs}
              documentsCount={documents.length}
            />
          </main>
        )}
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <PDFUploader
          onUploadSuccess={handleUploadSuccess}
          onClose={() => setUploadModalOpen(false)}
        />
      )}
    </div>
  );
}
