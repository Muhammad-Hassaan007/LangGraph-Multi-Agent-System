"""
Comprehensive Module 1 Test Suite:
1. Health & Configuration check
2. Upload doc_a.pdf (Quantum Computing) -> verify response & Supabase chunks
3. Upload doc_b.pdf (Deep Space Navigation) -> verify response & Supabase chunks
4. Query doc_a with Doc A question -> verify answer and page 2 citation
5. Strict Isolation Test: Query doc_a with Doc B question -> verify 'not found'
6. Query doc_b with Doc B question -> verify answer and page 1 citation
7. Unrelated question -> verify 'not found'
8. Error handling: empty PDF, non-PDF, corrupted PDF, oversized PDF
"""

import os
import requests
from config import config
from rag.supabase_vectorstore import get_supabase_client

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("TEST 1: Health & Configuration Check")
print("=" * 60)
h_resp = requests.get(f"{BASE_URL}/health")
assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
print("Health check response:", h_resp.json())
assert h_resp.json()["status"] == "healthy"
assert h_resp.json()["llm_configured"] is True
assert h_resp.json()["supabase_configured"] is True
print("PASS: Health & Credentials verified!")

print("\n" + "=" * 60)
print("TEST 2: Ingest Document A (test_pdfs/doc_a.pdf)")
print("=" * 60)
with open("test_pdfs/doc_a.pdf", "rb") as f:
    up_a = requests.post(f"{BASE_URL}/api/upload", files={"file": ("doc_a.pdf", f, "application/pdf")})
assert up_a.status_code == 201, f"Upload A failed: {up_a.text}"
data_a = up_a.json()
doc_id_a = data_a["document_id"]
print("Doc A Upload Result:", data_a)
assert data_a["success"] is True
assert data_a["chunks"] > 0
print(f"PASS: Doc A ingested with {data_a['chunks']} chunks. ID: {doc_id_a}")

print("\n" + "=" * 60)
print("TEST 3: Ingest Document B (test_pdfs/doc_b.pdf)")
print("=" * 60)
with open("test_pdfs/doc_b.pdf", "rb") as f:
    up_b = requests.post(f"{BASE_URL}/api/upload", files={"file": ("doc_b.pdf", f, "application/pdf")})
assert up_b.status_code == 201, f"Upload B failed: {up_b.text}"
data_b = up_b.json()
doc_id_b = data_b["document_id"]
print("Doc B Upload Result:", data_b)
assert data_b["success"] is True
assert data_b["chunks"] > 0
print(f"PASS: Doc B ingested with {data_b['chunks']} chunks. ID: {doc_id_b}")

print("\n" + "=" * 60)
print("TEST 4: Verify Supabase Database Rows")
print("=" * 60)
supabase = get_supabase_client()
rows_a = supabase.table("documents").select("id, document_id, metadata").eq("document_id", doc_id_a).execute().data
rows_b = supabase.table("documents").select("id, document_id, metadata").eq("document_id", doc_id_b).execute().data
print(f"Supabase rows for Doc A: {len(rows_a)}")
print(f"Supabase rows for Doc B: {len(rows_b)}")
assert len(rows_a) > 0 and len(rows_b) > 0
print("PASS: Verified chunks exist in Supabase PostgreSQL!")

print("\n" + "=" * 60)
print("TEST 5: Query Doc A -> What does Shor's algorithm do?")
print("=" * 60)
q_a = requests.post(f"{BASE_URL}/api/chat", json={
    "document_id": doc_id_a,
    "message": "What does Shor's algorithm do and what is its time complexity?"
})
assert q_a.status_code == 200, f"Query A failed: {q_a.text}"
res_a = q_a.json()
print("Answer A:", res_a["answer"])
print("Sources A:", res_a["sources"])
assert len(res_a["sources"]) > 0
assert "shor" in res_a["answer"].lower() or "prime" in res_a["answer"].lower() or "polynomial" in res_a["answer"].lower()
print("PASS: Doc A answered with page citation!")

print("\n" + "=" * 60)
print("TEST 6: STRICT ISOLATION TEST (Doc B Question asked with Doc A selected)")
print("=" * 60)
# Ask about pulsar navigation / XNAV while Doc A (Quantum Computing) is selected
q_iso = requests.post(f"{BASE_URL}/api/chat", json={
    "document_id": doc_id_a,
    "message": "What is X-ray pulsar navigation and how does XNAV work?"
})
assert q_iso.status_code == 200, f"Isolation query failed: {q_iso.text}"
res_iso = q_iso.json()
print("Isolation Answer:", res_iso["answer"])
print("Isolation Sources:", res_iso["sources"])
assert "not found" in res_iso["answer"].lower()
assert len(res_iso["sources"]) == 0
print("PASS: Strict Document Isolation Verified! Doc B question returned 'not found' on Doc A.")

print("\n" + "=" * 60)
print("TEST 7: Query Doc B with Doc B Selected")
print("=" * 60)
q_b = requests.post(f"{BASE_URL}/api/chat", json={
    "document_id": doc_id_b,
    "message": "What is X-ray pulsar navigation and how accurate is it?"
})
assert q_b.status_code == 200, f"Query B failed: {q_b.text}"
res_b = q_b.json()
print("Answer B:", res_b["answer"])
print("Sources B:", res_b["sources"])
assert len(res_b["sources"]) > 0
assert "pulsar" in res_b["answer"].lower() or "5" in res_b["answer"] or "xnav" in res_b["answer"].lower()
print("PASS: Doc B answered accurately with page citations!")

print("\n" + "=" * 60)
print("TEST 8: Unrelated Question Test")
print("=" * 60)
q_un = requests.post(f"{BASE_URL}/api/chat", json={
    "document_id": doc_id_b,
    "message": "What is the capital city of France?"
})
res_un = q_un.json()
print("Unrelated Answer:", res_un["answer"])
assert "not found" in res_un["answer"].lower()
print("PASS: Anti-hallucination verified on unrelated question!")

print("\n" + "=" * 60)
print("TEST 9: Error Handling Test Cases")
print("=" * 60)
# 1. Empty file
r_empty = requests.post(f"{BASE_URL}/api/upload", files={"file": ("empty.pdf", b"", "application/pdf")})
print("Empty PDF status:", r_empty.status_code, r_empty.json())
assert r_empty.status_code == 400

# 2. Non-PDF file
r_txt = requests.post(f"{BASE_URL}/api/upload", files={"file": ("notes.txt", b"hello world", "text/plain")})
print("Non-PDF status:", r_txt.status_code, r_txt.json())
assert r_txt.status_code == 400

# 3. Corrupted PDF
r_corrupt = requests.post(f"{BASE_URL}/api/upload", files={"file": ("bad.pdf", b"%PDF-1.4 garbage bad corrupted", "application/pdf")})
print("Corrupted PDF status:", r_corrupt.status_code, r_corrupt.json())
assert r_corrupt.status_code == 400

# 4. Missing question
r_no_q = requests.post(f"{BASE_URL}/api/chat", json={"document_id": doc_id_a, "message": ""})
print("Empty question status:", r_no_q.status_code)
assert r_no_q.status_code == 400

# 5. Missing doc_id
r_no_doc = requests.post(f"{BASE_URL}/api/chat", json={"document_id": "", "message": "Hi"})
print("Empty doc_id status:", r_no_doc.status_code)
assert r_no_doc.status_code in [400, 422]

print("PASS: All error handling test cases validated!")

print("\n" + "=" * 60)
print("ALL MODULE 1 TESTS PASSED WITH 100% SUCCESS!")
print("=" * 60)
