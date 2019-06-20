"""
This is a helper module for Flask's flash messages.

This module defines constants which represent available categories of flash
messages. These match to categories defined in `print_message` macro in
templates/macros.html file. If you modify macro and/or constants defined there,
make sure that they match.

More information about flash messages is available at
http://flask.pocoo.org/docs/0.10/patterns/flashing/.
"""
from flask import flash

_INFO = "info"  # this is a default category
_SUCCESS = "success"
_WARNING = "warning"
_ERROR = "error"

def info(message):
    flash(message, _INFO)

def success(message):
    flash(message, _SUCCESS)

def warning(message):
    flash(message, _WARNING)

def warn(message):
    """Alias for `warning`."""
    warning(message)

def error(message):
    flash(message, _ERROR)
