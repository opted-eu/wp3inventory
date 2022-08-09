import os
import secrets
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import has_request_context, request
from flaskinventory.misc import get_ip


class Config:
    SECRET_KEY = os.environ.get(
        'flaskinventory_SECRETKEY', secrets.token_hex(32))
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
    SLACK_LOGGING_ENABLED = os.environ.get('SLACK_LOGGING_ENABLED', False)
    SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')

    INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME", None)
    INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD", None)


""" Configure Logging """


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = get_ip()
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


def create_filehandler(name='main'):
    logging_path = os.path.abspath(os.path.join(os.getcwd(), 'logs'))
    if not os.path.exists(logging_path):
        os.makedirs(logging_path)
    file_handler = TimedRotatingFileHandler(
        os.path.join(logging_path, f'{name}.log'))
    formatter = RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s: '
        '%(levelname)s in %(module)s: %(message)s'
    )
    file_handler.setFormatter(formatter)
    return file_handler


class SlackHandler(logging.Handler):
    """
    A handler class which sends an Slack Message for each logging event.
    """

    def __init__(self, webhook):
        """
        Initialize the handler.
        """
        logging.Handler.__init__(self)

        self.webhook = webhook

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the webhook.
        """
        try:
            import requests

            message = {'text': self.format(record)}

            r = requests.post(self.webhook, json=message)

        except Exception:
            self.handleError(record)


def create_slackhandler(webhook):

    slck = SlackHandler(webhook)
    slck.setLevel(logging.ERROR)

    formatter = RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s: '
        '%(levelname)s in %(module)s: %(message)s'
    )
    slck.setFormatter(formatter)

    return slck
