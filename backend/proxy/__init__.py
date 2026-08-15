"""The mitmproxy side of AgentGuard. `traffic_interception.py` is what mitmweb
loads; it hands each flow to `addon.py`, where the whole request path is
visible in one place.
"""
