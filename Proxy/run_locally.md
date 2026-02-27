# =========== Instructions ============

# 1. Bash:

    # 1. cd AgentGuard/Proxy and then:

    # 2. python -m venv .venv

    # 3. .venv\Scripts\activate      # Windows
        # source .venv/bin/activate # macOS/Linux

    # 4. pip install -r requirements.txt

    # 5. mitmweb -s traffic_interception.py --listen-port 8080

# 2. Go to your settings, and in "Manual Proxy Set Up" set Address 127.0.0.1 and the port to 8080, and turn it on

# 3. Go to http://mitm.it/ (not HTTPS) and install a certificate that matches your OS