# 1. Bash:

    # 1. cd AgentGuard/Proxy
    # 2. python -m venv .venv
    # 3. .venv\Scripts\activate      # Windows
        # source .venv/bin/activate # macOS/Linux
    # 4. pip install -r requirements.txt
    # 5. mitmweb -s traffic_interception.py --listen-port 8080

# 2. In chrome://flags/ disable QUIC

# 3. Go to your system/browser settings, and in "Manual Proxy Set Up" set:
#       Address: 127.0.0.1
#       Port: 8080
#    Turn the proxy on

# 4. Open http://mitm.it/ (not HTTPS) and install the certificate that matches your OS