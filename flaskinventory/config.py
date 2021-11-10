import os
import secrets
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import has_request_context, request


class Config:
    SECRET_KEY = os.environ.get('flaskinventory_SECRETKEY', secrets.token_hex(32))
    DEBUG_MODE = os.environ.get('DEBUG_MODE', False)
    MAIL_SERVER = os.environ.get('EMAIL_SERVER', 'localhost')
    MAIL_PORT = os.environ.get('EMAIL_PORT', 25)
    MAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', False)
    MAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', False)
    MAIL_USERNAME = os.environ.get('EMAIL_USER', None)
    MAIL_PASSWORD = os.environ.get('EMAIL_PW', None)
    MAIL_DEFAULT_SENDER = os.environ.get('EMAIL_DEFAULT_SENDER', None)
    TWITTER_CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY', None)
    TWITTER_CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET', None)
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', None)
    TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET', None)
    VK_TOKEN = os.environ.get('VK_TOKEN', None)
    TELEGRAM_APP_ID = os.environ.get('TELEGRAM_APP_ID', None)
    TELEGRAM_APP_HASH = os.environ.get('TELEGRAM_APP_HASH', None)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', None)
    LOGGING_MAIL_ENABLED = os.environ.get('LOGGING_MAIL_ENABLED', False)
    LOGGING_MAIL_FROM = os.environ.get('MAIL_ERROR_FROM')
    LOGGING_MAIL_TO = os.environ.get('MAIL_ERROR_TO')


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


def create_mailhandler(mailhost, fromaddr, toaddr):

    if type(toaddr) != list:
        toaddr = [toaddr]

    from logging.handlers import SMTPHandler

    mail_handler = SMTPHandler(
        mailhost=mailhost,
        fromaddr=fromaddr,
        toaddrs=toaddr,
        subject='Application Error'
    )
    mail_handler.setLevel(logging.ERROR)
    formatter = RequestFormatter(
                '[%(asctime)s] %(remote_addr)s requested %(url)s: '
                '%(levelname)s in %(module)s: %(message)s'
                )
    mail_handler.setFormatter(formatter)

    return mail_handler