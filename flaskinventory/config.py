import os

class Config:
    SECRET_KEY = os.environ.get('flaskinventory_SECRETKEY')
    MAIL_SERVER = 'mail.univie.ac.at'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PW')