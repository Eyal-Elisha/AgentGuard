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

Flask will print the URL it is listening on (host and port come from `app.run()` in `backend/app.py`; default port is **5000** unless you change the code). The health route is **`/api/health`** on that server.
