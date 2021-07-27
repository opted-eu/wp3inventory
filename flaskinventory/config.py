import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('flaskinventory_SECRETKEY', secrets.token_hex(32))
    MAIL_SERVER = 'mail.univie.ac.at'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER', None)
    MAIL_PASSWORD = os.environ.get('EMAIL_PW', None)
    APP_VERSION = "0.2"
    TWITTER_CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY', None)
    TWITTER_CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET', None)
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', None)
    TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET', None)