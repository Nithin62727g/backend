import pymysql
import pymysql.cursors
from flask import g
from core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context (Flask's `g`).
    """
    if "db" not in g:
        try:
            logger.info(f"Connecting to DB at {settings.DB_HOST}:{settings.DB_PORT} as {settings.DB_USER}...")
            g.db = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                charset="utf8mb4",
                connect_timeout=5,
            )
            logger.debug("Opened new DB connection")
        except pymysql.MySQLError as e:
            logger.error(f"Failed to connect to MariaDB: {e}")
            raise e
    return g.db


def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()
        logger.debug("Closed DB connection")


def init_app(app):
    """Register close_db to be called when the app context tears down."""
    app.teardown_appcontext(close_db)
