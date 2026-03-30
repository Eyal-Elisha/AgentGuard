from __future__ import annotations

from mitmproxy import http

from backend.proxy.filters.response_filter import (
    should_log_request as rf_should_log_request,
    should_log_response as rf_should_log_response,
    is_browser_traffic as rf_is_browser_traffic,
)

def should_log_request(flow: http.HTTPFlow) -> bool:
    return rf_should_log_request(flow)


def should_log_response(flow: http.HTTPFlow) -> bool:
    return rf_should_log_response(flow)


def is_browser_traffic(flow: http.HTTPFlow) -> bool:
    return rf_is_browser_traffic(flow)


def is_eligible_for_response_analysis(flow: http.HTTPFlow) -> bool:
    return True
