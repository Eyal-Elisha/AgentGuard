"""High-level relevance gate for request analysis."""

from __future__ import annotations

from mitmproxy import http

from .actions import is_meaningful_user_action
from .assets import is_static_or_subresource
from .background import is_background_service_request
from .navigation import is_top_level_navigation
from .telemetry import is_tracking_or_telemetry


def is_relevant_for_analysis(flow: http.HTTPFlow) -> bool:
    if is_static_or_subresource(flow):
        return False

    if is_background_service_request(flow):
        return False

    if is_tracking_or_telemetry(flow):
        return False

    if is_top_level_navigation(flow):
        return True

    return is_meaningful_user_action(flow)
