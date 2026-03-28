from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urljoin
import re
from bs4 import BeautifulSoup


@dataclass
class FormDetails:
    action: str = ""
    method: str = "get"
    inputs: List[Dict[str, str]] = field(default_factory=list)
    action_host: str = ""


@dataclass
class DomFeatures:
    page_title: str = ""
    all_text_content: str = ""  # Every word on the page for Stage A to search
    forms: List[FormDetails] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)
    meta_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractedFeatures:
    url: str
    host: str
    scheme: str
    headers: Dict[str, str]
    is_html: bool
    raw_body: str = ""  # Kept for Stage B (LLM) if needed
    dom: Optional[DomFeatures] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeatureExtractor:
    def __init__(self, max_html_bytes: int = 512_000):
        self.max_html_bytes = max_html_bytes

    def extract(self, url: str, method: str, headers: Dict, body: Union[bytes, str]) -> ExtractedFeatures:
        parsed = urlparse(url)
        headers_lc = {str(k).lower(): str(v) for k, v in headers.items()}

        feats = ExtractedFeatures(
            url=url,
            host=parsed.hostname or "",
            scheme=parsed.scheme,
            headers=headers_lc,
            is_html="text/html" in headers_lc.get("content-type", "").lower()
        )

        if not feats.is_html or not body:
            return feats

        # Decode content once
        content = body[:self.max_html_bytes].decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        feats.raw_body = content

        soup = BeautifulSoup(content, "html.parser")
        dom = DomFeatures(
            page_title=soup.title.get_text(strip=True) if soup.title else "",
            all_text_content=soup.get_text(" ", strip=True)  # RAW TEXT
        )

        # Extract Forms
        for form in soup.find_all("form"):
            action = form.get("action", "")
            f_details = FormDetails(
                action=action,
                method=form.get("method", "get").lower(),
                action_host=urlparse(urljoin(url, action)).hostname or ""
            )
            # Just collect inputs, let Stage A decide if they are "sensitive"
            for inp in form.find_all("input"):
                f_details.inputs.append({
                    "type": inp.get("type", "text").lower(),
                    "name": inp.get("name", ""),
                    "id": inp.get("id", "")
                })
            dom.forms.append(f_details)

        # Inputs outside any <form> (common on sloppy / test / phishing pages)
        orphan_inputs: List[Dict[str, str]] = []
        for inp in soup.find_all("input"):
            if inp.find_parent("form") is not None:
                continue
            orphan_inputs.append({
                "type": inp.get("type", "text").lower(),
                "name": inp.get("name", ""),
                "id": inp.get("id", ""),
            })
        if orphan_inputs:
            dom.forms.append(
                FormDetails(
                    action="",
                    method="get",
                    action_host="",
                    inputs=orphan_inputs,
                )
            )

        # Extract Links and Scripts
        dom.links = [urljoin(url, a.get("href")) for a in soup.find_all("a", href=True)]
        dom.scripts = [urljoin(url, s.get("src")) for s in soup.find_all("script", src=True)]

        # Extract Meta Tags (e.g., for refresh rules)
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("http-equiv")
            if name:
                dom.meta_tags[name.lower()] = meta.get("content", "")

        feats.dom = dom
        return feats