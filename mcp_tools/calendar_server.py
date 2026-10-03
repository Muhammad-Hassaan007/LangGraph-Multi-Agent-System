"""
Google Calendar Model Context Protocol (MCP) Server.
"""

import sys
import os

# Prevent mcp_tools/ from shadowing standard library 'email' package
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from dateutil import parser as dt_parser

# Setup FastMCP server
mcp = FastMCP("calendar")

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_CALENDAR_FILE = BASE_DIR / "local_calendar.json"


def _load_local_events() -> List[Dict[str, Any]]:
    """Loads events from persistent local storage."""
    if not LOCAL_CALENDAR_FILE.exists():
        return []
    try:
        with open(LOCAL_CALENDAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_local_events(events: List[Dict[str, Any]]) -> None:
    """Saves events to persistent local storage."""
    with open(LOCAL_CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, default=str)


def _ensure_rfc3339(dt_str: str, default_tz: str = "Asia/Karachi") -> str:
    """Ensures datetime string is in RFC3339 format with timezone offset for Google Calendar API."""
    try:
        dt = dt_parser.parse(dt_str)
        if dt.tzinfo is None:
            import zoneinfo
            try:
                tz = zoneinfo.ZoneInfo(default_tz)
            except Exception:
                tz = datetime.timezone.utc
            dt = dt.replace(tzinfo=tz)
        return dt.isoformat()
    except Exception:
        return dt_str


def _send_direct_calendar_email(recipient: str, title: str, start_time: str, end_time: str, link: Optional[str] = None):
    """Sends an instant email notification to attendee using Gmail SMTP."""
    sender_addr = os.getenv("EMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("EMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    if not sender_addr or not app_pwd or not recipient:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = sender_addr
        msg["To"] = recipient
        msg["Subject"] = f"📅 Calendar Invitation / Meeting Scheduled: {title}"
        body_text = (
            f"Hello,\n\n"
            f"A calendar event has been scheduled:\n\n"
            f"📌 Title: {title}\n"
            f"⏰ Start Time: {start_time}\n"
            f"⏰ End Time: {end_time}\n"
            f"🌐 Timezone: Asia/Karachi\n"
        )
        if link:
            body_text += f"\n🔗 Google Calendar Event Link: {link}\n"
        body_text += f"\nBest regards,\nYour AI Multi-Agent System"
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(sender_addr, app_pwd)
            s.send_message(msg)
    except Exception as e:
        sys.stderr.write(f"Direct calendar email alert error: {e}\n")


def _get_google_service():
    """Attempts to build Google Calendar API service from OAuth token."""
    token_path = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", str(BASE_DIR / "token.json"))

    if not os.path.exists(token_path):
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events"
        ]
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
        if creds and creds.valid:
            return build("calendar", "v3", credentials=creds)
    except Exception as e:
        sys.stderr.write(f"Google Calendar OAuth error: {e}\n")
    return None


@mcp.tool()
def list_upcoming_events(max_results: int = 10) -> str:
    """
    Lists upcoming calendar events.
    Returns event title, start time, end time, and attendees.
    """
    service = _get_google_service()
    if service:
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            items = events_result.get("items", [])
            formatted = []
            for item in items:
                formatted.append({
                    "id": item.get("id"),
                    "title": item.get("summary", "Untitled"),
                    "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                    "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                    "attendees": [a.get("email") for a in item.get("attendees", [])],
                    "source": "google_calendar"
                })
            return json.dumps(formatted, indent=2)
        except Exception as e:
            sys.stderr.write(f"Error querying Google Calendar API: {e}\n")

    # Local storage fallback
    events = _load_local_events()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    upcoming = [e for e in events if e.get("end", "") >= now_iso or e.get("start", "") >= now_iso]
    upcoming.sort(key=lambda x: x.get("start", ""))
    return json.dumps(upcoming[:max_results], indent=2)


@mcp.tool()
def get_events_for_range(start_time: str, end_time: str) -> str:
    """
    Retrieves events that fall within a specified date/time range.
    Parameters:
        start_time: ISO-8601 string (e.g. '2026-10-05T09:00:00')
        end_time: ISO-8601 string (e.g. '2026-10-05T18:00:00')
    """
    start_iso = _ensure_rfc3339(start_time)
    end_iso = _ensure_rfc3339(end_time)

    service = _get_google_service()
    if service:
        try:
            events_result = service.events().list(
                calendarId="primary",
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            items = events_result.get("items", [])
            return json.dumps(items, indent=2)
        except Exception as e:
            sys.stderr.write(f"Google Calendar range query failed: {e}\n")

    events = _load_local_events()
    matched = []
    for e in events:
        e_start = e.get("start", "")
        e_end = e.get("end", "")
        if (e_start <= end_iso) and (e_end >= start_iso):
            matched.append(e)
    return json.dumps(matched, indent=2)


@mcp.tool()
def create_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
    timezone: str = "Asia/Karachi",
    check_conflicts: bool = True
) -> str:
    """
    Creates a new calendar event with conflict detection and automated email invitations.
    Parameters:
        title: Title of the meeting/event
        start_time: ISO format start time
        end_time: ISO format end time
        attendees: List of attendee email strings
        timezone: Timezone string (default 'Asia/Karachi')
        check_conflicts: If true, checks for overlapping events first
    """
    if attendees is None:
        attendee_list = []
    elif isinstance(attendees, str):
        try:
            attendee_list = json.loads(attendees)
        except Exception:
            attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
    else:
        attendee_list = list(attendees)

    start_iso = _ensure_rfc3339(start_time, timezone)
    end_iso = _ensure_rfc3339(end_time, timezone)

    # Conflict checking
    if check_conflicts:
        conflicts_str = get_events_for_range(start_iso, end_iso)
        conflicts = json.loads(conflicts_str)
        if conflicts:
            return json.dumps({
                "status": "conflict_detected",
                "message": f"⚠️ Conflict detected: {len(conflicts)} event(s) already scheduled during this timeframe.",
                "conflicting_events": conflicts,
                "requested_event": {
                    "title": title,
                    "start": start_iso,
                    "end": end_iso
                }
            }, indent=2)

    service = _get_google_service()
    if service:
        try:
            # Add configured system user so they also receive invitation alert
            cfg_user = os.getenv("EMAIL_ADDRESS", "").strip()
            if cfg_user and cfg_user not in attendee_list:
                attendee_list.append(cfg_user)

            body = {
                "summary": title,
                "start": {"dateTime": start_iso, "timeZone": timezone},
                "end": {"dateTime": end_iso, "timeZone": timezone},
                "attendees": [{"email": email} for email in attendee_list],
            }
            # sendUpdates="all" sends official Google Calendar invitations to all attendee inboxes
            created = service.events().insert(
                calendarId="primary",
                body=body,
                sendUpdates="all"
            ).execute()
            cal_link = created.get("htmlLink")

            # Dispatch direct SMTP confirmation to attendee inboxes
            for email in attendee_list:
                _send_direct_calendar_email(email, title, start_iso, end_iso, cal_link)

            return json.dumps({
                "status": "created",
                "id": created.get("id"),
                "title": title,
                "start": start_iso,
                "end": end_iso,
                "attendees": attendee_list,
                "link": cal_link,
                "source": "google_calendar",
                "email_notifications_sent": True
            }, indent=2)
        except Exception as e:
            sys.stderr.write(f"Google Calendar insert failed: {e}\n")

    # Local store fallback
    events = _load_local_events()
    new_event = {
        "id": f"evt_{uuid.uuid4().hex[:10]}",
        "title": title,
        "start": start_iso,
        "end": end_iso,
        "attendees": attendee_list,
        "timezone": timezone,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "local_calendar"
    }
    events.append(new_event)
    _save_local_events(events)

    # Dispatch direct email in local mode as well
    for email in attendee_list:
        _send_direct_calendar_email(email, title, start_iso, end_iso)

    return json.dumps({
        "status": "created",
        "event": new_event,
        "message": f"Successfully created event '{title}' from {start_iso} to {end_iso}."
    }, indent=2)


@mcp.tool()
def update_event(
    event_id: str,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Updates an existing calendar event by ID."""
    service = _get_google_service()
    if service:
        try:
            patch_body = {}
            if title:
                patch_body["summary"] = title
            if start_time:
                patch_body["start"] = {"dateTime": start_time}
            if end_time:
                patch_body["end"] = {"dateTime": end_time}
            updated = service.events().patch(calendarId="primary", eventId=event_id, body=patch_body).execute()
            return json.dumps({"status": "updated", "id": updated.get("id")}, indent=2)
        except Exception as e:
            sys.stderr.write(f"Google Calendar patch failed: {e}\n")

    events = _load_local_events()
    found = False
    for e in events:
        if e.get("id") == event_id:
            found = True
            if title:
                e["title"] = title
            if start_time:
                e["start"] = start_time
            if end_time:
                e["end"] = end_time
            break

    if not found:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."}, indent=2)

    _save_local_events(events)
    return json.dumps({"status": "updated", "id": event_id}, indent=2)


@mcp.tool()
def delete_event(event_id: str) -> str:
    """Deletes a calendar event by ID."""
    service = _get_google_service()
    if service:
        try:
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return json.dumps({"status": "deleted", "id": event_id}, indent=2)
        except Exception as e:
            sys.stderr.write(f"Google Calendar delete failed: {e}\n")

    events = _load_local_events()
    filtered = [e for e in events if e.get("id") != event_id]
    _save_local_events(filtered)
    return json.dumps({"status": "deleted", "id": event_id, "message": f"Event {event_id} deleted."}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
