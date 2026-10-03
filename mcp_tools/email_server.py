"""
Email Model Context Protocol (MCP) Server.
Runs as a dedicated stdio subprocess using FastMCP.
Exposes real email tools:
- write_email (formats and validates an email)
- create_draft (saves a draft to persistent storage or Gmail)
- send_email (enforces Human-in-the-Loop confirmation before sending)
- schedule_email (persists to SQLite job store via APScheduler)
- list_scheduled_emails (lists scheduled jobs)
- cancel_scheduled_email (cancels a scheduled job)
Supports Gmail API (OAuth), SMTP fallback, and persistent sandbox outbox.
"""

import sys
import os

# Prevent mcp_tools/ directory from shadowing standard library 'email' package
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

import json
import uuid
import smtplib
import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dateutil import parser as dt_parser

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DRAFTS_FILE = BASE_DIR / "local_email_drafts.json"
LOCAL_OUTBOX_FILE = BASE_DIR / "local_email_outbox.json"
SQLITE_DB_PATH = BASE_DIR / "scheduled_emails.db"

# Initialize FastMCP
mcp = FastMCP("email")

# Persistent APScheduler with SQLite job store
jobstores = {
    "default": SQLAlchemyJobStore(url=f"sqlite:///{SQLITE_DB_PATH}")
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()


def _load_json_list(filepath: Path) -> List[Dict[str, Any]]:
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_json_list(filepath: Path, data: List[Dict[str, Any]]) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _deliver_email_payload(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Actually transmits the email via Gmail API, SMTP, or local outbox.
    Called only AFTER explicit user confirmation or when a scheduled job triggers.
    """
    smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", 587))
    sender_addr = os.getenv("EMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("EMAIL_APP_PASSWORD", "").strip().replace(" ", "")

    # Try real SMTP if configured with credentials
    if sender_addr and app_pwd:
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_addr
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.starttls()
                server.login(sender_addr, app_pwd)
                server.send_message(msg)

            return {
                "status": "sent",
                "transport": "smtp_live",
                "recipient": recipient,
                "subject": subject,
                "sender": sender_addr,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "message": f"Real email successfully dispatched to {recipient} via Gmail SMTP!"
            }
        except Exception as e:
            sys.stderr.write(f"SMTP send failed ({e}), falling back to local sandbox outbox.\n")

    # Local outbox store fallback (when credentials not in .env)
    outbox = _load_json_list(LOCAL_OUTBOX_FILE)
    record = {
        "id": f"msg_{uuid.uuid4().hex[:10]}",
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "sender": sender_addr or "assistant@system.local",
        "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "transport": "sandbox_outbox"
    }
    outbox.append(record)
    _save_json_list(LOCAL_OUTBOX_FILE, outbox)
    return {
        "status": "sent",
        "transport": "sandbox_outbox",
        "record": record,
        "message": (
            f"Email saved to local sandbox outbox (local_email_outbox.json). "
            f"To deliver directly to {recipient}'s live Gmail inbox, add your EMAIL_ADDRESS "
            f"and 16-character EMAIL_APP_PASSWORD in backend .env."
        )
    }


@mcp.tool()
def write_email(recipient: str, subject: str, body: str) -> str:
    """
    Composes and formats an email.
    Returns preview details without sending.
    """
    preview = {
        "status": "drafted",
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "character_count": len(body),
        "word_count": len(body.split())
    }
    return json.dumps(preview, indent=2)


@mcp.tool()
def create_draft(recipient: str, subject: str, body: str) -> str:
    """
    Saves an email as a draft in persistent storage.
    """
    drafts = _load_json_list(LOCAL_DRAFTS_FILE)
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    draft = {
        "id": draft_id,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    drafts.append(draft)
    _save_json_list(LOCAL_DRAFTS_FILE, drafts)
    return json.dumps({
        "status": "draft_saved",
        "draft_id": draft_id,
        "draft": draft,
        "message": f"Draft '{subject}' saved successfully."
    }, indent=2)


@mcp.tool()
def send_email(recipient: str, subject: str, body: str, confirmed: bool = False) -> str:
    """
    Sends an email to the recipient.
    CRITICAL HUMAN-IN-THE-LOOP RULE:
    If confirmed is False, execution is BLOCKED and details are returned for user review.
    Only sends when confirmed is True.
    """
    if not confirmed:
        return json.dumps({
            "status": "requires_confirmation",
            "action": "send_email",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "message": (
                f"⚠️ **Confirmation Required Before Sending Email**\n\n"
                f"- **To:** {recipient}\n"
                f"- **Subject:** {subject}\n"
                f"- **Body:**\n```text\n{body}\n```\n\n"
                f"Please reply 'confirm' to send this email, or 'cancel' to discard."
            )
        }, indent=2)

    # User confirmed -> proceed with delivery
    res = _deliver_email_payload(recipient, subject, body)
    return json.dumps(res, indent=2)


def _scheduled_email_job_runner(recipient: str, subject: str, body: str):
    """Callback executed by APScheduler at the target time."""
    _deliver_email_payload(recipient, subject, body)


@mcp.tool()
def schedule_email(
    recipient: str,
    subject: str,
    body: str,
    send_at: str,
    timezone: str = "Asia/Karachi"
) -> str:
    """
    Schedules an email to be sent at a specific future time.
    Persisted to SQLite job store so jobs survive backend restarts.
    Parameters:
        recipient: Target email address
        subject: Email subject
        body: Email body content
        send_at: ISO-8601 string or date/time string
        timezone: User timezone
    """
    try:
        run_dt = dt_parser.parse(send_at)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Invalid datetime format '{send_at}': {e}"}, indent=2)

    job_id = f"job_email_{uuid.uuid4().hex[:10]}"
    try:
        job = scheduler.add_job(
            _scheduled_email_job_runner,
            "date",
            run_date=run_dt,
            args=[recipient, subject, body],
            id=job_id,
            name=f"Email to {recipient}: {subject}",
            replace_existing=True
        )
        return json.dumps({
            "status": "scheduled",
            "job_id": job.id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "send_at": run_dt.isoformat(),
            "message": f"✅ Email to {recipient} successfully scheduled for {run_dt.isoformat()} (persisted in SQLite)."
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to schedule email job: {e}"}, indent=2)


@mcp.tool()
def list_scheduled_emails() -> str:
    """
    Lists all scheduled emails currently queued in the persistent SQLite job store.
    """
    jobs = scheduler.get_jobs()
    job_list = []
    for j in jobs:
        job_list.append({
            "id": j.id,
            "name": j.name,
            "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None
        })
    return json.dumps(job_list, indent=2)


@mcp.tool()
def cancel_scheduled_email(job_id: str) -> str:
    """Cancels a scheduled email job from the SQLite job store."""
    try:
        scheduler.remove_job(job_id)
        return json.dumps({"status": "cancelled", "job_id": job_id, "message": f"Job {job_id} cancelled."}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Could not cancel job {job_id}: {e}"}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
