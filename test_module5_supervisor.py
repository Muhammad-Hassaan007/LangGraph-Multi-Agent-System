"""
Module 5 Test Suite: LangGraph Supervisor & Multi-Agent Orchestration.
Tests:
1. Chit-chat / Greeting: Supervisor handles directly
2. Document / RAG Routing: Routes to rag_agent and returns sources
3. GitHub Routing: Routes to github_agent
4. Calendar Routing: Routes to calendar_agent
5. Email Routing: Routes to email_agent
"""

import sys
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from supervisor import process_user_query
from rag.ingest import process_and_index_pdf


async def test_module5():
    print("=" * 60)
    print("MODULE 5 TEST 1: Supervisor Direct Greeting / Chit-chat")
    print("=" * 60)
    res_greet = await process_user_query("Hello there! What can you help me with?")
    print("Sender:", res_greet["sender"])
    print("Answer:\n", res_greet["answer"])
    assert res_greet["sender"] == "supervisor"
    print("PASS: Supervisor responded directly without delegating chit-chat!")

    print("\n" + "=" * 60)
    print("MODULE 5 TEST 2: Supervisor -> RAG Agent Routing")
    print("=" * 60)
    # Ingest doc_a.pdf to get a fresh document_id
    with open("test_pdfs/doc_a.pdf", "rb") as f:
        ingest_res = process_and_index_pdf(f.read(), "doc_a.pdf")
    doc_id = ingest_res["document_id"]
    res_rag = await process_user_query(
        query="What is Shor's algorithm and what is its time complexity according to the document?",
        document_id=doc_id
    )
    print("Sender:", res_rag["sender"])
    print("Answer:\n", res_rag["answer"])
    print("Sources:", len(res_rag.get("sources", [])))
    assert res_rag["sender"] == "rag_agent"
    assert "shor" in res_rag["answer"].lower() or "prime" in res_rag["answer"].lower()
    print("PASS: Supervisor accurately routed document query to RAG Sub-Agent!")

    print("\n" + "=" * 60)
    print("MODULE 5 TEST 3: Supervisor -> GitHub Agent Routing")
    print("=" * 60)
    res_gh = await process_user_query("What is the README content of octocat/Hello-World repository on GitHub?")
    print("Sender:", res_gh["sender"])
    print("Answer:\n", res_gh["answer"][:300] + "...")
    assert res_gh["sender"] == "github_agent"
    assert "Hello World" in res_gh["answer"] or "README" in res_gh["answer"]
    print("PASS: Supervisor accurately routed GitHub query to GitHub Sub-Agent!")

    print("\n" + "=" * 60)
    print("MODULE 5 TEST 4: Supervisor -> Google Calendar Agent Routing")
    print("=" * 60)
    res_cal = await process_user_query("Do I have any meetings scheduled on my calendar?")
    print("Sender:", res_cal["sender"])
    print("Answer:\n", res_cal["answer"])
    assert res_cal["sender"] == "calendar_agent"
    print("PASS: Supervisor accurately routed calendar query to Calendar Sub-Agent!")

    print("\n" + "=" * 60)
    print("MODULE 5 TEST 5: Supervisor -> Email Agent Routing")
    print("=" * 60)
    res_em = await process_user_query("Draft an email to advisor@university.edu with subject 'Semester Update'")
    print("Sender:", res_em["sender"])
    print("Answer:\n", res_em["answer"])
    assert res_em["sender"] == "email_agent"
    assert "advisor@university.edu" in res_em["answer"] or "Semester Update" in res_em["answer"]
    print("PASS: Supervisor accurately routed email query to Email Sub-Agent!")

    print("\n" + "=" * 60)
    print("ALL MODULE 5 SUPERVISOR TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_module5())
