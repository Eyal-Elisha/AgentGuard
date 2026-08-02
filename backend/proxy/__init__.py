"""The mitmproxy side of AgentGuard: what runs inside the intercepting proxy.

`traffic_interception.py` is what mitmweb loads. It hands each flow to
`addon.py`, which is the one place the whole request path is visible:

    filter_requests  is this flow even worth analysing?
    prompting        append the fallback instruction to outbound LLM bodies
    warn_bypass      has the user already clicked "Continue anyway" here?
    decision_client  ask the backend for a verdict
    enforcement      turn that verdict into a response
    interstitials    render the Warn and Block pages
    audit            record the session, the event and every rule analysis

The proxy holds the browser's connection open while the backend evaluates, so
everything here sits on the critical path of the user's browsing.
"""
