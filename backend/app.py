from . import create_app
from .config import env_flag, server_port
from backend.settings import get_api_host

app = create_app()


def main() -> None:
    """Run the local backend API server."""
    app.run(
        host=get_api_host(),
        port=server_port(),
        debug=env_flag("FLASK_DEBUG", default=False),
    )


if __name__ == "__main__":
    main()
