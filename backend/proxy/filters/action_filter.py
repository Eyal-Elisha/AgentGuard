from mitmproxy import http

def is_action_request(flow: http.HTTPFlow) -> bool:
    method = flow.request.method.upper()

    if method in ["POST", "PUT", "PATCH", "DELETE", "GET"]:
        return True

    return False