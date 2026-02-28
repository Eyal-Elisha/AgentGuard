from mitmproxy import http
import json
import datetime

def request(flow: http.HTTPFlow):
    data = {
        "timestamp": str(datetime.datetime.now()),
        "type": "request",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "headers": dict(flow.request.headers),
        "body": flow.request.get_text()
    }

    print(json.dumps(data, indent=2))


def response(flow: http.HTTPFlow):
    data = {
        "timestamp": str(datetime.datetime.now()),
        "type": "response",
        "status_code": flow.response.status_code,
        "url": flow.request.pretty_url,
        "headers": dict(flow.response.headers),
        "body": flow.response.get_text()
    }

    print(json.dumps(data, indent=2))