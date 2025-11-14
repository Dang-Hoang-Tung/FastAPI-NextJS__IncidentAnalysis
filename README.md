# AI-Enhanced Incident Response Analysis

This is an AI analysis system that processes social care call/meeting data, analyses it against organisation policies, and generates appropriate responses.

## How to run

Set Env:
- `export OPENAI_API_KEY=sk...`

Option 1. Using Docker:
- `docker compose up --build`
- Go to localhost:3000 to try it

Option 2. Manually:
- cd into backend/app: `uvicorn main:app --reload`
- cd into frontend/app: `npm run dev`
- Go to localhost:3000 to try it
