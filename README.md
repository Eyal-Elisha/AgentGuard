# AgentGuard

## Backend layout

Modular Python package under `backend/`:

| Package | Role |
|--------|------|
| `routes/` | HTTP API routing |
| `analysis/` | Analysis logic |
| `storage/` | Persistence (SQLite) |

Entry: `python -m backend.app` (Flask app factory in `backend/__init__.py`).

## Requirements

- **Python 3.12+** — required by `mitmproxy==12.x`. Python 3.9 (Apple system default on macOS) and 3.11 are too old.
  - macOS: `brew install python@3.12`
  - Windows / Linux: download from [python.org](https://www.python.org/downloads/) or your package manager.
- **Node.js 18+** — for the Vite/React frontend.

## Environment (venv + dependencies)

From the **repository root** (where `requirements.txt` lives):

1. Create a virtual environment using Python 3.12:
   - **macOS / Linux:** `python3.12 -m venv .venv`
   - **Windows:** `py -3.12 -m venv .venv`
2. Activate it:
   - **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
   - **Windows (cmd):** `.venv\Scripts\activate.bat`
   - **macOS / Linux:** `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`

> **macOS note:** `mitmproxy-windows` and `pydivert` are automatically skipped on macOS/Linux via `sys_platform` markers in `requirements.txt`. `mitmproxy-macos` is pulled in automatically as a transitive dependency of `mitmproxy_rs`.

## Configuration

Configuration is loaded from `backend/.env`. Copy `backend/.env.example` to `backend/.env`. The example file lists keys only (no sample values); you must set `JWT_SECRET`, and you may leave the other variables blank to use built-in defaults. Optional settings:

- `JWT_SECRET`: long random secret used to sign and verify JWTs
- `REQUIRE_AUTH`: `true` to require bearer tokens on protected routes (default off when unset)
- `FLASK_DEBUG`: `true` to run the dev server with Flask debug mode (default off when unset)
- `PORT`: HTTP port for the Flask dev server (default **3000** when unset or invalid)
- `DATABASE_URL`: SQLite URL; if unset, the app defaults to `backend/agentguard.db` under the package
- `API_HOST` / `API_PORT`: used by the **mitmproxy addon** to build the URL for `POST /api/proxy/decision`. If `API_PORT` is unset, **`PORT` is used** so the proxy and Flask stay aligned.
- `PROXY_PORT`: listen port for the local proxy (`python proxy_launcher.py`; default **8080**)
- `AGENTGUARD_BACKEND_TIMEOUT_SECONDS`, `AGENTGUARD_BACKEND_FAILURE_MODE`: proxy → backend behavior (see `backend/.env.example`)

## Run the backend

With the venv activated, from the repository root:

```bash
python -m backend.app
```

Flask will print the URL it is listening on (host and port come from `app.run()` in `backend/app.py`; default port is **3000** when `PORT` is unset or invalid). The health route is **`/health`** on that server.

## Run the proxy

From the repository root:

```bash
python proxy_launcher.py
```

The proxy listen port comes from `PROXY_PORT` in `backend/.env` and defaults to `8080`.

### Configuring the system proxy

After the proxy is running, point your browser or OS at it (`127.0.0.1:8080` by default):

- **macOS:** System Settings → Network → select your interface → Details → Proxies → enable *Web Proxy (HTTP)* and *Secure Web Proxy (HTTPS)*, set server `127.0.0.1` port `8080`.
- **Windows:** Settings → Network & Internet → Proxy → Manual proxy setup, address `127.0.0.1` port `8080`.
- **Browser (any OS):** set a manual HTTP/HTTPS proxy to `127.0.0.1:8080`.

### Installing the mitmproxy CA certificate

Visit `http://mitm.it/` while the proxy is active and follow the OS-specific instructions.

- **macOS:** After downloading the `.pem`, open it in Keychain Access, find the *mitmproxy* certificate, open it, expand *Trust*, and set *When using this certificate* to **Always Trust**.
- **Windows:** Run the downloaded `.p12` installer and place the certificate in the *Trusted Root Certification Authorities* store.

## Run tests

```bash
python -m unittest discover -s tests/backend -p "test_*.py" -v
```
