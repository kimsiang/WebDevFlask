"""Request-scoped MySQL access with explicit, environment-based configuration."""

import os

from flask import current_app, g
import pymysql


class DatabaseUnavailable(Exception):
    """Database settings are incomplete; no connection should be attempted."""


def configure_database(app, overrides=None):
    defaults = {
        "DB_HOST": "127.0.0.1", "DB_PORT": 3306,
        "DB_USER": "", "DB_PASSWORD": "", "DB_NAME": "",
        "DB_CONNECT_TIMEOUT": 5, "DB_READ_TIMEOUT": 10,
        "DB_WRITE_TIMEOUT": 10, "DB_SSL_CA": "",
    }
    app.config.from_mapping({key: os.environ.get(key, value) for key, value in defaults.items()})
    if overrides:
        app.config.update(overrides)
    for key in ("DB_PORT", "DB_CONNECT_TIMEOUT", "DB_READ_TIMEOUT", "DB_WRITE_TIMEOUT"):
        try:
            raw = app.config[key]
            value = int(raw)
            if isinstance(raw, bool) or str(raw).strip() != str(value):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"{key} must be a positive integer") from None
        maximum = 65535 if key == "DB_PORT" else 31536000 if key == "DB_CONNECT_TIMEOUT" else None
        if value < 1 or (maximum is not None and value > maximum):
            raise ValueError(f"{key} is outside the supported range")
        app.config[key] = value


def get_db():
    """Open one connection per application context, only when a route needs it."""
    if "db" not in g:
        config = current_app.config
        if not config["DB_USER"] or not config["DB_NAME"]:
            raise DatabaseUnavailable("DB_USER and DB_NAME are required")
        options = {
            "host": config["DB_HOST"], "port": config["DB_PORT"],
            "user": config["DB_USER"], "password": config["DB_PASSWORD"],
            "database": config["DB_NAME"], "charset": "utf8mb4",
            "connect_timeout": config["DB_CONNECT_TIMEOUT"],
            "read_timeout": config["DB_READ_TIMEOUT"],
            "write_timeout": config["DB_WRITE_TIMEOUT"],
            "autocommit": True, "local_infile": False,
        }
        if config["DB_SSL_CA"]:
            options.update(ssl_ca=config["DB_SSL_CA"], ssl_verify_cert=True, ssl_verify_identity=True)
        try:
            g.db = pymysql.connect(**options)
        except OSError as error:
            # TLS CA loading happens before PyMySQL wraps socket errors. Keep
            # unavailable certificate files on the same controlled error path.
            raise DatabaseUnavailable("Database connection could not be initialized") from error
    return g.db


def query(sql, parameters=()):
    """Execute a fixed SELECT, close its cursor, and return rows plus column names."""
    cursor = get_db().cursor()
    try:
        cursor.execute(sql, parameters)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return rows, columns
    finally:
        cursor.close()


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        try:
            connection.close()
        except pymysql.MySQLError:
            current_app.logger.warning("Database connection was already unavailable during cleanup")
