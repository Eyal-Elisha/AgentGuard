from .config import env_flag, load_environment, server_port
from . import create_app

load_environment()

app = create_app()


if __name__ == "__main__":
    app.run(debug=env_flag("FLASK_DEBUG"), port=server_port())
