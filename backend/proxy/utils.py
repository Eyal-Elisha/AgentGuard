import json
import datetime

def safe_get_text(message):
    if not message or not message.content:
        return ""

    try:
        return message.get_text()

    except Exception:
        return f"<{len(message.content)} bytes binary>"

def build_request_data(flow):
    return {
        "timestamp": str(datetime.datetime.now()),
        "type": "REQUEST",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "headers": dict(flow.request.headers),
        "body": safe_get_text(flow.request)
    }

def build_response_data(flow):
    return {
        "timestamp": str(datetime.datetime.now()),
        "type": "RESPONSE",
        "status_code": flow.response.status_code,
        "url": flow.request.pretty_url,
        "headers": dict(flow.response.headers),
        "body": safe_get_text(flow.response)
    }

def pretty_print(title, data):
    print(f"\n===== {title} =====")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"===== End =====\n")