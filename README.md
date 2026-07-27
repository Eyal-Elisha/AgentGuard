# AgentGuard

## macOS prerequisites

AgentGuard needs Python and Node.js. With [Homebrew](https://brew.sh/) installed:

```bash
brew install python@3.13 node
```

Python 3.13 is recommended for compatibility with the pinned proxy dependencies.

## Backend layout

Modular Python package under `backend/`:

| Package | Role |
|--------|------|
| `routes/` | HTTP API routing |
| `analysis/` | Analysis logic |
| `storage/` | Persistence (SQLite) |

Entry: `python -m backend.app` (Flask app factory in `backend/__init__.py`).

## Environment (venv + dependencies)

From the **repository root** (where `requirements.txt` lives):

1. Create a virtual environment: `python3.13 -m venv .venv`
2. Activate it:
   - **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
   - **Windows (cmd):** `.venv\Scripts\activate.bat`
   - **macOS / Linux:** `source .venv/bin/activate`
3. Install dependencies: `python -m pip install -r requirements.txt`

## Configuration

Configuration is loaded from `backend/.env`. Copy `backend/.env.example` to `backend/.env`. The example file lists keys only (no sample values); you must set `JWT_SECRET`, and you may leave the other variables blank to use built-in defaults. Optional settings:

- `JWT_SECRET`: long random secret used to sign and verify JWTs
- `REQUIRE_AUTH`: `true` to require bearer tokens on protected routes (default off when unset)
- `FLASK_DEBUG`: `true` to run the dev server with Flask debug mode (default off when unset)
- `PORT`: HTTP port for the Flask dev server (default **3000** when unset or invalid)
- `DATABASE_URL`: SQLite URL; if unset, the app defaults to `backend/agentguard.db` under the package
- `AGENTGUARD_LOG_ENCRYPTION_KEY`: Fernet key used to encrypt audit JSONL records, event URLs/headers/risk scores, and rule-analysis scores/details before they are stored. Required before persisting logs. Generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- `API_HOST` / `API_PORT`: used by the **mitmproxy addon** to build the URL for `POST /api/proxy/decision`. If `API_PORT` is unset, **`PORT` is used** so the proxy and Flask stay aligned.
- `PROXY_PORT`: listen port for the local proxy (`python proxy_launcher.py`; default **8080**)
- `AGENTGUARD_BACKEND_TIMEOUT_SECONDS`, `AGENTGUARD_BACKEND_FAILURE_MODE`: proxy → backend behavior (see `backend/.env.example`)

## Run the backend

With the venv activated, from the repository root:

```bash
python -m backend.app
```

Flask will print the URL it is listening on (host and port come from `app.run()` in `backend/app.py`; default port is **3000** when `PORT` is unset or invalid). The health route is **`/health`** on that server.

## Run the frontend

In a second Terminal window, from the repository root:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `VITE_BACKEND_URL=http://127.0.0.1:3000` in `frontend/.env`. Then open
`http://localhost:5173`.

## Run the proxy

In a third Terminal window, from the repository root with the virtual
environment activated:

```bash
python proxy_launcher.py
```

The proxy listen port comes from `PROXY_PORT` in `backend/.env` and defaults to `8080`.

## Run tests

```bash
python -m unittest discover -s tests/backend -p "test_*.py" -v
```
