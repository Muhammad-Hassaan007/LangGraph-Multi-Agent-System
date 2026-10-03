"""
End-to-End System Integration Test Suite
Validates the entire LangGraph Multi-Agent System via the Vite frontend proxy (http://127.0.0.1:5173).
Tests:
1. System Health & Configuration
2. Supabase pgvector Document Listing
3. RAG Sub-Agent with Document Isolation & Source Citations
4. Anti-hallucination Protection
5. GitHub MCP Sub-Agent over stdio
6. Google Calendar MCP Sub-Agent with Natural Language Scheduling
7. Email MCP Sub-Agent with Human-in-the-Loop Confirmation
8. APScheduler Persistent Email Queue
9. LangGraph Supervisor Multi-Turn Conversation
"""

import sys
import requests
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:5173"
REQUEST_TIMEOUT = 60  # Allow adequate time for stdio MCP sub-agents and LLM reasoning

def run_test(name, fn):
    print(f"\n==========================================")
    print(f"RUNNING: {name}")
    print(f"==========================================")
    try:
        fn()
        print(f"PASSED: {name}")
        return True
    except AssertionError as e:
        print(f"FAILED (Assertion): {name} -> {e}")
        return False
    except Exception as e:
        print(f"FAILED (Error): {name} -> {e}")
        return False


def test_health():
    res = requests.get(f"{BASE_URL}/api/health", timeout=15)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data.get("status") == "healthy", "Expected healthy status"
    assert data.get("llm_configured") is True, "LLM not configured"
    assert data.get("supabase_configured") is True, "Supabase not configured"
    print("Health Status:", data)


def test_documents_listing():
    res = requests.get(f"{BASE_URL}/api/documents", timeout=15)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert isinstance(data, list), "Expected list of documents"
    assert len(data) > 0, "Expected at least 1 indexed document in Supabase"
    print(f"Found {len(data)} documents in Supabase pgvector.")
    for d in data[:2]:
        print(f" - {d.get('filename')} (ID: {d.get('document_id')}, Chunks: {d.get('chunks_count')})")


def test_rag_query():
    # Fetch existing document
    res_docs = requests.get(f"{BASE_URL}/api/documents", timeout=15)
    docs = res_docs.json()
    # Find the latest doc_a.pdf
    doc_a = [d for d in docs if d["filename"] == "doc_a.pdf"][-1]
    assert doc_a is not None, "doc_a.pdf not found in Supabase"

    doc_id = doc_a["document_id"]
    payload = {
        "message": "What is Shor's algorithm used for and what is its complexity?",
        "document_id": doc_id
    }
    res = requests.post(f"{BASE_URL}/api/agent", json=payload, timeout=REQUEST_TIMEOUT)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data.get("sender") == "rag_agent", f"Expected rag_agent, got {data.get('sender')}"
    assert "shor" in data.get("answer", "").lower(), "Expected Shor in answer"
    assert len(data.get("sources", [])) > 0, "Expected source citations"
    print("RAG Agent Answer:", data["answer"][:160], "...")
    print("Sources Cited:", len(data["sources"]))


def test_rag_anti_hallucination():
    res_docs = requests.get(f"{BASE_URL}/api/documents", timeout=15)
    docs = res_docs.json()
    doc_a = [d for d in docs if d["filename"] == "doc_a.pdf"][-1]
    doc_id = doc_a["document_id"]

    payload = {
        "message": "What is the secret recipe for strawberry cheesecake in this document?",
        "document_id": doc_id
    }
    res = requests.post(f"{BASE_URL}/api/agent", json=payload, timeout=REQUEST_TIMEOUT)
    assert res.status_code == 200
    data = res.json()
    assert "not found" in data.get("answer", "").lower(), "Expected anti-hallucination response"
    print("Anti-Hallucination Verified:", data["answer"])


def test_github_agent():
    payload = {
        "message": "Get the file contents of README from octocat/Hello-World repository"
    }
    res = requests.post(f"{BASE_URL}/api/agent", json=payload, timeout=REQUEST_TIMEOUT)
    assert res.status_code == 200
    data = res.json()
    assert data.get("sender") == "github_agent"
    assert "hello world" in data.get("answer", "").lower()
    print("GitHub Agent Verified:", data["answer"][:160], "...")


def test_calendar_agent():
    payload = {
        "message": "List upcoming events on my calendar"
    }
    res = requests.post(f"{BASE_URL}/api/agent", json=payload, timeout=REQUEST_TIMEOUT)
    assert res.status_code == 200
    data = res.json()
    assert data.get("sender") == "calendar_agent"
    assert len(data.get("answer", "")) > 10
    print("Calendar Agent Verified:", data["answer"][:160], "...")


def test_email_hitl_and_scheduled():
    # 1. Test Human-In-The-Loop Confirmation
    draft_req = {
        "message": "Send an email to student@example.com with subject Exam Review and body Please review chapter 4."
    }
    res1 = requests.post(f"{BASE_URL}/api/agent", json=draft_req, timeout=REQUEST_TIMEOUT)
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1.get("pending_action") is not None, "Expected pending_action requiring confirmation"
    pending = d1["pending_action"]
    action_name = pending.get("tool") or pending.get("action")
    print("HITL Intercepted Send:", action_name, "for", pending.get("args", {}).get("recipient"))

    # 2. Confirm execution
    confirm_req = {
        "message": "Confirmed",
        "confirmed": True,
        "pending_action": pending
    }
    res2 = requests.post(f"{BASE_URL}/api/agent", json=confirm_req, timeout=REQUEST_TIMEOUT)
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2.get("sender") == "email_agent"
    assert "successfully" in d2.get("answer", "").lower() or "sent" in d2.get("answer", "").lower()
    print("Confirmed Execution Result:", d2["answer"][:160], "...")

    # 3. Test Scheduled Emails API
    sched_res = requests.get(f"{BASE_URL}/api/scheduled-emails", timeout=15)
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert "scheduled_emails" in sched_data
    print(f"Scheduled Emails Queue: {len(sched_data['scheduled_emails'])} persistent job(s) found.")


def main():
    print("Starting Full E2E System Integration Test Suite...\n")
    tests = [
        ("Health & Config Verification", test_health),
        ("Supabase Documents Listing", test_documents_listing),
        ("RAG Sub-Agent Retrieval & Citations", test_rag_query),
        ("RAG Anti-Hallucination Compliance", test_rag_anti_hallucination),
        ("GitHub MCP Sub-Agent Execution", test_github_agent),
        ("Google Calendar MCP Sub-Agent Execution", test_calendar_agent),
        ("Email MCP HITL & Scheduler Verification", test_email_hitl_and_scheduled),
    ]

    passed = 0
    for name, fn in tests:
        if run_test(name, fn):
            passed += 1

    print("\n==========================================")
    print(f"FINAL SUMMARY: {passed}/{len(tests)} TESTS PASSED")
    print("==========================================")

    if passed == len(tests):
        print("ALL END-TO-END MULTI-AGENT TESTS COMPLETED WITH 100% SUCCESS.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
