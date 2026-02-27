from __future__ import annotations
from typing import Any, Mapping, Optional, Union

from .feature_extractor import FeatureExtractor, ExtractedFeatures


_default_extractor = FeatureExtractor(max_html_bytes=512_000)

def extract_features_for_event(
    *,
    request_url: str,
    request_method: str,
    request_headers: Optional[Mapping[str, Any]] = None,
    query_params: Optional[Mapping[str, Any]] = None,
    response_headers: Optional[Mapping[str, Any]] = None,
    response_body: Optional[Union[bytes, str]] = None,
    event_type: str = "generic",
    high_impact_event: Optional[bool] = None,
) -> ExtractedFeatures:
    """
    Central place to define the handling logic.
    Later will base it on actual business logic
    """

    if high_impact_event is None:
        # simple starter:
        high_impact_event = event_type.lower() in {"login", "payment", "checkout", "password_change", "credentials"}

    return _default_extractor.extract(
        request_url=request_url,
        request_method=request_method,
        request_headers=request_headers,
        query_params=query_params,
        response_headers=response_headers,
        response_body=response_body,
        high_impact_event=high_impact_event,
    )