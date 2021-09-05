from config import Config
from flask import Flask
from flask_httpauth import HTTPTokenAuth
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
auth_token = HTTPTokenAuth(scheme="Bearer")


def create_app(config=Config):
    """app factory

    Args:
        config: Config object for app.config

    Returns:
        Flask app
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # blueprint registering
    from app.main import bp as bp_main
    app.register_blueprint(bp_main)

    from app.auth import bp as bp_auth
    app.register_blueprint(bp_auth)

    from app.api import bp as bp_api
    app.register_blueprint(bp_api, url_prefix='/api')

    return app

if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
