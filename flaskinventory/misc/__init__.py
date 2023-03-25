from flask import request
from flask import current_app

def get_ip() -> str:
    if current_app.config['TESTING']:
        return '0.0.0.0'
    if request.environ.get('HTTP_X_REAL_IP'):
        return request.environ.get('HTTP_X_REAL_IP')
    elif request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ.get('HTTP_X_FORWARDED_FOR')
    else:
        return request.environ['REMOTE_ADDR']