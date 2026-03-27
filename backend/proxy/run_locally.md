# 1. Bash:

    # 1. .venv\Scripts\activate      # Windows
        # source .venv/bin/activate # macOS/Linux
    # 2. pip install -r requirements.txt
    # 3. cd backend/proxy
    # 4. mitmweb -s traffic_interception.py --listen-port *PORT FROM .env*

# 2. In chrome://flags/ disable QUIC

# 3. Go to your system/browser settings, and in "Manual Proxy Set Up" set:
#       Address: 127.0.0.1
#       Port: *PORT FROM .env*
#    Turn the proxy on

# 4. Open http://mitm.it/ (not HTTPS) and install the certificate that matches your OS