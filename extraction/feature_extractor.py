from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import urlparse, parse_qs
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(".feature_extractor")

@dataclass
class RequestMetadata:
    url: str = ""
    method: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, list[str]] = field(default_factory=dict)
    host: str = ""
    scheme: str = ""
    path: str = ""

@dataclass
class DomFeatures:
    parsed: bool = False
    parse_error: Optional[str] = None
    truncated: bool = False
    has_password_field: bool = False
    has_login_form: bool = False
    form_action_host: Optional[str] = None
    form_action_host_mismatch: bool = False

@dataclass
class ExtractedFeatures:
    request: RequestMetadata
    response_is_html: bool = False
    dom: DomFeatures = field(default_factory=DomFeatures)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def _lowercase_headers(headers: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in headers.items():
        if k is None:
            continue
        key = str(k).strip().lower()
        if isinstance(v, (list, tuple)):
            out[key] = ", ".join(str(x) for x in v)
        else:
            out[key] = str(v)
    return out

def _safe_parse_url(url: str):
    try:
        return urlparse(url)
    except Exception:
        return urlparse("")

def _is_html_response(headers_lc: Mapping[str, str], body_bytes: Optional[bytes]) -> bool:
    ct = headers_lc.get("content-type", "")
    if "text/html" in ct.lower():
        return True
    if not body_bytes:
        return False
    sample = body_bytes[:512].lstrip()
    return sample.startswith(b"<!doctype html") or sample.startswith(b"<html") or b"<html" in sample[:256].lower()

def _decode_body(body: bytes, headers_lc: Mapping[str, str]) -> str:
    ct = headers_lc.get("content-type", "")
    charset = "utf-8"
    if "charset=" in ct.lower():
        charset = ct.lower().split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except Exception:
        return body.decode("utf-8", errors="replace")

def _effective_form_action_url(action: str, base_url: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base_url, action)

class FeatureExtractor:
    def __init__(self, *, max_html_bytes: int = 512_000) -> None:
        self.max_html_bytes = int(max_html_bytes)

    def extract(
        self,
        *,
        request_url: str,
        request_method: str,
        request_headers: Optional[Mapping[str, Any]] = None,
        query_params: Optional[Mapping[str, Any]] = None,
        response_headers: Optional[Mapping[str, Any]] = None,
        response_body: Optional[Union[bytes, str]] = None,
        high_impact_event: bool = False,
    ) -> ExtractedFeatures:
        req_headers_lc = _lowercase_headers(request_headers or {})
        res_headers_lc = _lowercase_headers(response_headers or {})

        parsed = _safe_parse_url(request_url)
        host = parsed.hostname or ""
        scheme = parsed.scheme or ""
        path = parsed.path or ""

        if query_params is not None:
            qp_out: Dict[str, list[str]] = {}
            for k, v in query_params.items():
                if isinstance(v, (list, tuple)):
                    qp_out[str(k)] = [str(x) for x in v]
                else:
                    qp_out[str(k)] = [str(v)]
        else:
            qp_out = {k: [str(x) for x in v] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}

        req = RequestMetadata(
            url=request_url or "",
            method=(request_method or "").upper(),
            headers=dict(req_headers_lc),
            query_params=qp_out,
            host=host,
            scheme=scheme,
            path=path,
        )

        features = ExtractedFeatures(request=req)

        body_bytes: Optional[bytes]
        if response_body is None:
            body_bytes = None
        elif isinstance(response_body, bytes):
            body_bytes = response_body
        else:
            body_bytes = str(response_body).encode("utf-8", errors="replace")

        is_html = _is_html_response(res_headers_lc, body_bytes)
        features.response_is_html = is_html

        if not (high_impact_event and is_html and body_bytes):
            return features

        dom = DomFeatures()
        features.dom = dom

        if len(body_bytes) > self.max_html_bytes:
            dom.truncated = True
            body_bytes = body_bytes[: self.max_html_bytes]

        try:
            html_text = _decode_body(body_bytes, res_headers_lc)
            soup = BeautifulSoup(html_text, "html.parser")

            dom.parsed = True
            dom.has_password_field = soup.select_one('input[type="password"]') is not None

            forms = soup.find_all("form")
            dom.has_login_form = False
            chosen_form_action_host: Optional[str] = None

            for form in forms:
                if form.select_one('input[type="password"]') is not None:
                    dom.has_login_form = True
                else:
                    userish = form.select_one(
                        'input[name*="user" i], input[name*="email" i], input[id*="user" i], input[id*="email" i]'
                    )
                    if userish is not None:
                        dom.has_login_form = True

                if chosen_form_action_host is None:
                    action = (form.get("action") or "").strip()
                    if action:
                        abs_action = _effective_form_action_url(action, request_url)
                        action_host = _safe_parse_url(abs_action).hostname
                        if action_host:
                            chosen_form_action_host = action_host

                if dom.has_login_form and chosen_form_action_host is not None:
                    break

            dom.form_action_host = chosen_form_action_host
            if dom.form_action_host and req.host:
                dom.form_action_host_mismatch = (dom.form_action_host.lower() != req.host.lower())

        except Exception as e:
            dom.parsed = False
            dom.parse_error = f"{type(e).__name__}: {e}"
            logger.warning("HTML parse failed: %s", dom.parse_error, exc_info=True)

        return features