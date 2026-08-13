"""Helpers for reading query parameters from Flask requests."""

from flask import request


def get_param(name):
    """Return a single request parameter with optional fallback handling."""
    value = None
    try:
        value = request.args.get(name, None)
    except:
        pass
    if value is None:
        try:
            value = request.form[name]
        except:
            pass
    return value


def get_params(list_in):
    """Return all request parameters as a normalized dictionary."""
    params = {
        "callback": None
    }
    for key in list_in.keys():
        value = get_param(key)
        if value is None:
            params[key] = list_in[key]
        else:
            params[key] = value
    return params
