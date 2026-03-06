from flask import Flask

from .config import load_config
from .routes.admin_routes import admin_bp
from .routes.public_routes import public_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_mapping(load_config())

    app.secret_key = app.config["SECRET_KEY"]
    app.permanent_session_lifetime = app.config["PERMANENT_SESSION_LIFETIME"]

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    return app
