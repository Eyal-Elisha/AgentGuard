from mitmproxy import http

def is_action_request(flow: http.HTTPFlow) -> bool:
    method = flow.request.method.upper()
    has_body = bool(flow.request.content)

    # Only meaningful actions
    if method in ["POST", "PUT", "PATCH"]:
        return True

    if method == "GET" and has_body:
        return True

    return False