from config import Config
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

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

    # blueprint registering
    from app.main import bp as bp_main
    app.register_blueprint(bp_main)

    from app.api import bp as bp_api
    app.register_blueprint(bp_api, url_prefix='/api')

    return app

if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    from sqlalchemy.engine import Engine
    from sqlalchemy import event

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
