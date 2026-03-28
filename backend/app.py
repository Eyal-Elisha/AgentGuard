from . import create_app
from backend.feature_extraction.feature_extractor import FeatureExtractor
from urllib.request import Request, urlopen
import json
import logging

app = create_app()

logging.basicConfig(level=logging.INFO)

def fetch_site(url: str) -> tuple[dict, bytes]:
    """
    Fetches the target URL and returns headers and raw body bytes.
    """
    req = Request(url, headers={
        "User-Agent": "AgentGuard/1.0",
        "Accept": "text/html"
    })
    with urlopen(req, timeout=15) as resp:
        return dict(resp.headers), resp.read()


if __name__ == "__main__":
    # Test URL
    target_url = "https://is.colman.ac.il/nidp/saml2/sso?id=colman&sid=0&option=credential&sid=0"

    try:
        logging.info(f"Fetching: {target_url}")
        response_headers, response_body = fetch_site(target_url)

        extractor = FeatureExtractor()

        extracted_features = extractor.extract(
            url=target_url,
            method="GET",
            headers=response_headers,
            body=response_body
        )

        result = extracted_features.to_dict()
        display_data = {
            "url": result.get("url"),
            "host": result.get("host"),
            "form_count": len(result.get("dom", {}).get("forms", [])),
            "has_password": any("password" in str(f).lower() for f in result.get("dom", {}).get("forms", []))
        }

        print("\n--- EXTRACTION SUMMARY ---")
        print(json.dumps(display_data, indent=2))

        logging.info("Extraction completed successfully.")

    except Exception as e:
        logging.error(f"Extraction failed: {e}")

    app.run(debug=True)
