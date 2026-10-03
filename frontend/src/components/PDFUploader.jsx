import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  X 
} from 'lucide-react';

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB limit

export default function PDFUploader({ onUploadSuccess, onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | uploading | processing | success | error
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const validateAndSetFile = (file) => {
    setErrorMessage('');
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setErrorMessage('Unsupported file type. Please select a valid PDF (.pdf) file.');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMessage(`File exceeds the 25 MB limit (${formatFileSize(file.size)}).`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setStatus('idle');
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setStatusMessage('Uploading PDF to server...');
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Step: Ingesting into Supabase pgvector
      setStatus('processing');
      setStatusMessage('Extracting text, chunking & generating Supabase pgvector embeddings...');

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed. Please try again.');
      }

      setStatus('success');
      const count = data.chunks ?? data.chunks_count ?? 0;
      setStatusMessage(`Indexed ${count} chunks into Supabase. Document is ready!`);

      setTimeout(() => {
        onUploadSuccess(data);
      }, 1200);
    } catch (err) {
      console.error('Upload Error:', err);
      setStatus('error');
      setErrorMessage(err.message || 'An unexpected error occurred during processing.');
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h3 className="modal-title">Upload Knowledge PDF</h3>
            <p className="modal-desc">
              Your document will be chunked, embedded, and stored in Supabase pgvector.
            </p>
          </div>
          {onClose && (
            <button className="btn-close" onClick={onClose}>
              <X size={18} />
            </button>
          )}
        </div>

        {/* Dropzone */}
        <div
          className={`dropzone ${dragActive ? 'drag-active' : ''} ${
            selectedFile ? 'has-file' : ''
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          {!selectedFile ? (
            <div className="dropzone-content">
              <div className="dropzone-icon">
                <UploadCloud size={36} />
              </div>
              <p className="dropzone-label">
                Drag & drop your PDF here, or <span className="browse-link">browse</span>
              </p>
              <span className="dropzone-hint">Supports PDF documents up to 25 MB</span>
            </div>
          ) : (
            <div className="file-preview">
              <FileText size={32} className="file-preview-icon" />
              <div className="file-preview-meta">
                <p className="file-preview-name">{selectedFile.name}</p>
                <p className="file-preview-size">{formatFileSize(selectedFile.size)}</p>
              </div>
              <button
                type="button"
                className="btn-change-file"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  setStatus('idle');
                }}
              >
                Change
              </button>
            </div>
          )}
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="alert-message error">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Processing / Progress message */}
        {(status === 'uploading' || status === 'processing') && (
          <div className="alert-message info">
            <Loader2 size={16} className="spin-icon" />
            <span>{statusMessage}</span>
          </div>
        )}

        {/* Success message */}
        {status === 'success' && (
          <div className="alert-message success">
            <CheckCircle2 size={16} />
            <span>{statusMessage}</span>
          </div>
        )}

        {/* Modal Actions */}
        <div className="modal-actions">
          {onClose && (
            <button
              type="button"
              className="btn-cancel"
              onClick={onClose}
              disabled={status === 'uploading' || status === 'processing'}
            >
              Cancel
            </button>
          )}

          <button
            type="button"
            className="btn-upload"
            onClick={handleUpload}
            disabled={
              !selectedFile ||
              status === 'uploading' ||
              status === 'processing' ||
              status === 'success'
            }
          >
            {status === 'uploading' || status === 'processing' ? (
              <>
                <Loader2 size={16} className="spin-icon" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <UploadCloud size={16} />
                <span>Process & Index PDF</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
