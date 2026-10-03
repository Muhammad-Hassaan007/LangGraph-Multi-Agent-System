import React, { useState, useEffect } from 'react';
import { Mail, Clock, Trash2, X, Loader2, CheckCircle2 } from 'lucide-react';

export default function ScheduledEmailsModal({ onClose }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState(null);
  const [message, setMessage] = useState('');

  const fetchScheduledJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/scheduled-emails');
      if (res.ok) {
        const data = await res.json();
        const emailList = Array.isArray(data.scheduled_emails)
          ? data.scheduled_emails
          : [];
        setJobs(emailList);
      }
    } catch (err) {
      console.error('Failed to load scheduled emails:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduledJobs();
  }, []);

  const handleCancelJob = async (jobId) => {
    setCancellingId(jobId);
    try {
      const res = await fetch(`/api/scheduled-emails/${jobId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setJobs((prev) => prev.filter((j) => (j.id || j.job_id) !== jobId));
        setMessage('Scheduled email cancelled successfully.');
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      console.error('Failed to cancel job:', err);
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card scheduled-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="flex-center-gap">
            <Mail size={20} className="text-accent" />
            <div>
              <h3 className="modal-title">Persistent Scheduled Emails</h3>
              <p className="modal-desc">
                Queued in SQLite job store via APScheduler
              </p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Message Banner */}
        {message && (
          <div className="alert-message success">
            <CheckCircle2 size={16} />
            <span>{message}</span>
          </div>
        )}

        {/* Content */}
        <div className="scheduled-jobs-content">
          {loading ? (
            <div className="empty-state-small">
              <Loader2 size={24} className="spin-icon" />
              <span>Loading scheduled emails...</span>
            </div>
          ) : jobs.length === 0 ? (
            <div className="empty-state-small">
              <Clock size={32} className="text-dim" />
              <p>No pending scheduled emails in queue.</p>
              <span className="hint-text">
                Ask the Email MCP agent: "Schedule an email to user@example.com tomorrow at 10am"
              </span>
            </div>
          ) : (
            <div className="scheduled-jobs-list">
              {jobs.map((job) => {
                const jobId = job.id || job.job_id || 'unknown';
                const runAt = job.next_run_time || job.run_at;
                return (
                  <div key={jobId} className="scheduled-job-card">
                    <div className="job-card-main">
                      <div className="job-subject">
                        <strong>{job.name || job.subject || 'Scheduled Email'}</strong>
                      </div>
                      {job.recipient && (
                        <div className="job-recipient">
                          <strong>To:</strong> {job.recipient}
                        </div>
                      )}
                      <div className="job-run-time">
                        <Clock size={12} />
                        <span>
                          {runAt ? new Date(runAt).toLocaleString() : 'Scheduled'}
                        </span>
                        <span className="source-badge" style={{ marginLeft: '8px' }}>
                          ID: {jobId}
                        </span>
                      </div>
                      {job.body && (
                        <p className="job-preview-body">
                          "{job.body.length > 100 ? job.body.slice(0, 100) + '...' : job.body}"
                        </p>
                      )}
                    </div>

                    <button
                      className="btn-cancel-job"
                      title="Cancel scheduled email"
                      disabled={cancellingId === jobId}
                      onClick={() => handleCancelJob(jobId)}
                    >
                      {cancellingId === jobId ? (
                        <Loader2 size={14} className="spin-icon" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      <span>Cancel</span>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-actions">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
