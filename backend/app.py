import logging

from . import create_app
from backend.settings import get_api_host, get_api_port

app = create_app()

logging.basicConfig(level=logging.INFO)


def main() -> None:
    """Run the local backend API server."""
    app.run(host=get_api_host(), port=get_api_port(), debug=False)


if __name__ == "__main__":
    main()
