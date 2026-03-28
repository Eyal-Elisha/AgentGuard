import os

from .config import load_environment, server_port
from . import create_app

load_environment()

app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug, port=server_port())
