"""Mitmproxy addon: log flows and run Stage A on eligible HTML responses (see `response_analysis.py`)."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.filter_requests import should_forward
from backend.proxy.filters.analysis_eligibility import should_log_request, should_log_response
from backend.proxy.response_analysis import analyze_response_safe
from backend.proxy.utils import build_request_data, pretty_print, response_data_with_evaluation


def request(flow: http.HTTPFlow):
    if not should_forward(flow):
        return
    if not should_log_request(flow):
        return

    data = build_request_data(flow)
    pretty_print(f"{flow.request.method} {flow.request.host}", data)


def response(flow: http.HTTPFlow):
    if not (should_forward(flow) and flow.response):
        return
    if not should_log_response(flow):
        return

    result = analyze_response_safe(flow)
    data = response_data_with_evaluation(flow, result)
    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)
