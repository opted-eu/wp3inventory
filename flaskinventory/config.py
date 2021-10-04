import os
import secrets
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import has_request_context, request


class Config:
    SECRET_KEY = os.environ.get('flaskinventory_SECRETKEY', secrets.token_hex(32))
    MAIL_SERVER = 'mail.univie.ac.at'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER', None)
    MAIL_PASSWORD = os.environ.get('EMAIL_PW', None)
    APP_VERSION = "0.3"
    TWITTER_CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY', None)
    TWITTER_CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET', None)
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', None)
    TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET', None)
    VK_TOKEN = os.environ.get('VK_TOKEN')
    
""" Configure Logging """


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


def create_filehandler(name='main'):
    logging_path = os.path.abspath(os.path.join(os.getcwd(), 'logs'))
    if not os.path.exists(logging_path):
        os.makedirs(logging_path)
    file_handler = TimedRotatingFileHandler(os.path.join(logging_path, f'{name}.log'))
    formatter = RequestFormatter(
                '[%(asctime)s] %(remote_addr)s requested %(url)s: '
                '%(levelname)s in %(module)s: %(message)s'
                )
    file_handler.setFormatter(formatter)
    return file_handler