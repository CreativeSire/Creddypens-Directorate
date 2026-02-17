## CreddyPens Backend (FastAPI)

### Prereqs
- Python 3.11+ (you have 3.14)
- Postgres 14+ (local or Docker)

### Quickstart (local)
1. Create a venv, then install deps:
   - `python -m venv .venv`
   - `.venv\\Scripts\\Activate.ps1`
   - `pip install -r requirements.txt`
2. Set env vars (copy and edit):
   - `Copy-Item .env.example .env`
3. Start Postgres and apply the schema:
   - If using Docker: from repo root run `docker compose up -d db`
   - Then run: `docker compose exec -T db psql -U postgres -d creddypens -f /docker-entrypoint-initdb.d/init.sql`
4. Seed the 3 MVP agents:
   - `python .\\scripts\\seed_agents.py`
5. Run the API:
   - `uvicorn app.main:app --reload --port 8000`

### First endpoint
- `GET /health`
- `GET /v1/agents`
