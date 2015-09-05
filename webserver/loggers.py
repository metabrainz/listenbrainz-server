import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from raven.contrib.flask import Sentry


def init_loggers(app):
    if "LOG_FILE_ENABLED" in app.config and app.config["LOG_FILE_ENABLED"]:
        _add_file_handler(app, app.config["LOG_FILE"], level=logging.INFO)
    if "LOG_EMAIL_ENABLED" in app.config and app.config["LOG_EMAIL_ENABLED"]:
        _add_email_handler(app, logging.ERROR)
    if "LOG_SENTRY_ENABLED" in app.config and app.config["LOG_SENTRY_ENABLED"]:
        _add_sentry(app, logging.INFO)


def _add_file_handler(app, filename, max_bytes=512 * 1024, backup_count=100,
                      level=logging.NOTSET):
    """Adds file logging."""
    file_handler = RotatingFileHandler(filename, maxBytes=max_bytes,
                                       backupCount=backup_count)
    file_handler.setLevel(level)
    app.logger.addHandler(file_handler)


def _add_email_handler(app, level=logging.NOTSET):
    """Adds email notifications about captured logs."""
    mail_handler = SMTPHandler(
        (app.config["SMTP_SERVER"], app.config["SMTP_PORT"]),
        "logs@" + app.config["MAIL_FROM_DOMAIN"],
        app.config["LOG_EMAIL_RECIPIENTS"],
        app.config["LOG_EMAIL_TOPIC"]
    )
    mail_handler.setLevel(level)
    mail_handler.setFormatter(logging.Formatter("""
    Message type: %(levelname)s
    Location: %(pathname)s:%(lineno)d
    Module: %(module)s
    Function: %(funcName)s
    Time: %(asctime)s
    Message:
    %(message)s
    """))
    app.logger.addHandler(mail_handler)


def _add_sentry(app, level=logging.NOTSET):
    """Adds support for error logging and aggregation using Sentry platform.
    
    See https://docs.getsentry.com for more information about it.
    """
    Sentry(app, logging=True, level=level)
