@echo off
echo Starting FastAPI Backend...
call .venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
pause
