# AgentGuard

## Backend layout

Modular Python package under `backend/`:

| Package | Role |
|--------|------|
| `routes/` | HTTP API routing |
| `analysis/` | Analysis logic (future) |
| `storage/` | Persistence (future) |
| `models/` | Data models (future) |

Entry: `python -m backend.app` (Flask app factory in `backend/__init__.py`).

## Environment (venv + dependencies)

From the **repository root** (where `requirements.txt` lives):

1. Create a virtual environment: `python -m venv .venv`
2. Activate it:
   - **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
   - **Windows (cmd):** `.venv\Scripts\activate.bat`
   - **macOS / Linux:** `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`

## Run the backend

With the venv activated, from the repository root:

```bash
python -m backend.app
```

Configuration is loaded from `backend/.env`. Copy `backend/.env.example` to `backend/.env`. The example file lists keys only (no sample values); you must set `JWT_SECRET`, and you may leave the other variables blank to use built-in defaults. Optional settings:

- `JWT_SECRET`: long random secret used to sign and verify JWTs
- `REQUIRE_AUTH`: `true` to require bearer tokens on protected routes (default off when unset)
- `FLASK_DEBUG`: `true` only for local debugging (default off when unset)
- `PORT`: HTTP port for the dev server (default **3000** when unset or invalid)
- `DATABASE_URL`: SQLite URL; if unset, the app defaults to `backend/agentguard.db` under the package

Flask will print the URL it is listening on (host and port come from `app.run()` in `backend/app.py`; default port is **3000** when `PORT` is unset or invalid). The health route is **`/health`** on that server.

## Run tests

```bash
python -m unittest discover -s tests/backend -p "test_*.py" -v
```
