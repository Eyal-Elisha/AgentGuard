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
| `proxy/` | The mitmproxy addon: traffic triage, enforcement, interstitials, audit |
| `analysis/` | The rule engine: rule definitions, the two evaluation stages, scoring |
| `feature_extraction/` | HTML → the features the rules read |
| `routes/` | HTTP API routing |
| `validation/` | Request validation, one module per request family |
| `storage/` | Persistence (SQLite) |

Entry: `python -m backend.app` (Flask app factory in `backend/__init__.py`).

**[`backend/ARCHITECTURE.md`](backend/ARCHITECTURE.md) traces one request from
interception through to storage and says which file does what.** Start there.

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
- `PROXY_PORT`: base of the interception range; the first agent in the catalogue listens here (default **8080**)
- `PROXY_WEB_PORT`: base of the administrative range, which mitmweb's own interface is served from (default **8180**). A separate base rather than an offset, because mitmweb puts its interface on the port immediately above its interception port
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
python proxy_launcher.py --agent BrowserOS
```

One proxy instance protects one agent, and several can run at once. Each agent
gets its own two ports, allocated from its position in the catalogue so the
endpoint you configure in the agent never moves:

| Agent | Point the agent at | mitmweb's own interface |
|---|---|---|
| `AllTraffic` (default) | 8080 | 8180 |
| `BrowserOS` | 8081 | 8181 |
| `MicrosoftEdge` | 8082 | 8182 |

`AllTraffic` is the catch-all: it is not tied to a named agent, so point
the system proxy at it and anything honouring system proxy settings is
protected. It keeps 8080, the port the proxy has always listened
on. Omitting `--agent` uses it. The bases come from `PROXY_PORT` and
`PROXY_WEB_PORT` in `backend/.env`. All instances share one certificate
authority, so the certificate is installed once.

The Guard screen in the dashboard does the same thing: pick one or more agents
(All traffic by default), and one power button starts and stops the lot. Each
selected agent shows its own endpoint beside its live status.

## Run tests

With the venv activated, from the repository root:

```bash
python -m pytest -q
```

Run it from that virtual environment rather than a system Python — the proxy
tests import `mitmproxy`, and collection fails without it. Tests marked
`integration` make real network requests and are deselected by default; run
them with `python -m pytest -m integration`.
