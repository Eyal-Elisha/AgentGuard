1. Activate the virtual environment.
   Windows: `.venv\Scripts\activate`
   macOS/Linux: `source .venv/bin/activate`

2. Install dependencies from the repo root.
   `pip install -r requirements.txt`

3. Configure optional proxy enforcement settings in `backend/.env`.
   - `API_PORT=3000`
   - `PROXY_PORT=8080`
   - `AGENTGUARD_BACKEND_TIMEOUT_SECONDS=10`
   - `AGENTGUARD_BACKEND_FAILURE_MODE=fail_closed`
   - Custom blacklist entries live in `backend/proxy/custom_blacklist.txt`

4. Start the backend API from the repo root.
   `python -m backend.app`

5. Start the proxy from the repo root.
   `python proxy_launcher.py`

   The launcher reads `PROXY_PORT` from `backend/.env` and starts `mitmweb` with that listen port.

6. In `chrome://flags/`, disable QUIC.

7. In your system/browser proxy settings, enable a manual proxy:
   - Address: `127.0.0.1`
   - Port: the `PROXY_PORT` value from `backend/.env` (for example `8080`)

8. Open `http://mitm.it/` and install the certificate that matches your OS.

If you prefer to start mitmweb manually, use:
   From the repo root:
   `mitmweb -s backend/proxy/traffic_interception.py --listen-port <PROXY_PORT>`

If the backend decision API is unreachable, the proxy follows `AGENTGUARD_BACKEND_FAILURE_MODE`.
`fail_closed` blocks the request with a 503 response; `fail_open` allows the request and logs the backend failure.