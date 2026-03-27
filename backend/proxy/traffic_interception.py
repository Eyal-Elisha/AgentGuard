from mitmproxy import http
from backend.proxy.filter_requests import should_forward
from utils import build_request_data, build_response_data, pretty_print

def request(flow: http.HTTPFlow):
    if not should_forward(flow):
        return

    data = build_request_data(flow)

    pretty_print(f"{flow.request.method} {flow.request.host}", data)


def response(flow: http.HTTPFlow):
    if not should_forward(flow):
        return

    if not flow.response:
        return

    data = build_response_data(flow)

    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)