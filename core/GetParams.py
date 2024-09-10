from flask import request


def get_param(name):
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
