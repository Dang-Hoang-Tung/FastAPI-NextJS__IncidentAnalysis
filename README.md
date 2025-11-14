# AI-Enhanced Incident Response Analysis

This is an AI analysis system that processes social care call/meeting data, analyses it against organisation policies, and generates appropriate responses.

## Demo screenshot

<img width="881" height="948" alt="image" src="https://github.com/user-attachments/assets/fe0f7e66-3fd7-439a-bb6a-541143141952" />

## Codebase overview

As this is a prototype, I kept the codebase structure as simple as possible.

All backend code is in `backend/app/main.py`
- APIs
- LangChain models (fallback + structured output)
- LangChain chains
- RAG system
- Logging

All frontend code is in `frontend/app/page.tsx`
- Inputs
- Fetching logic
- Displaying to user

## How to run locally

Firstly, set env var:
- `export OPENAI_API_KEY=sk...`

Option 1. Using Docker:
- `docker compose up --build`
- Go to localhost:3000 to try it

Option 2. Manually:
- cd into backend/app:
  - `python -m venv venv && source venv/bin/activate`
  - `pip install -r requirements.txt`
  - `uvicorn main:app --reload`
- cd into frontend/app: 
  - `npm install`
  - `npm run dev`
- Go to localhost:3000 to try it
