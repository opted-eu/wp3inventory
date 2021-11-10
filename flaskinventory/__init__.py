import logging
import json

from flask import Flask
from .config import create_filehandler, create_mailhandler

from flask_login import LoginManager, AnonymousUserMixin
from flask_mail import Mail
from flaskinventory.config import Config
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flaskinventory.flaskdgraph import DGraph

dgraph = DGraph()


class AnonymousUser(AnonymousUserMixin):
    user_role = 0


login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
login_manager.anonymous_user = AnonymousUser


mail = Mail()

limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config, config_json=None):
    app = Flask(__name__)

    app.logger.addHandler(create_filehandler())

    if config_json:
        app.config.from_file(config_json, json.load)
    else:
        app.config.from_object(config_class)

    if app.config.get('DEBUG_MODE'):
        app.debug = True
    
    if app.debug:
        app.logger.setLevel(logging.DEBUG)

    app.config['APP_VERSION'] = "0.8"

    from flaskinventory.users.routes import users
    from flaskinventory.view.routes import view
    from flaskinventory.add.routes import add
    from flaskinventory.edit.routes import edit
    from flaskinventory.review.routes import review
    from flaskinventory.main.routes import main
    from flaskinventory.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(view)
    app.register_blueprint(add)
    app.register_blueprint(edit)
    app.register_blueprint(review)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    dgraph.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    if app.config.get('LOGGING_MAIL_ENABLED'):
        try:
            mail_handler = create_mailhandler(mail, app.config['LOGGING_MAIL_FROM'], app.config['LOGGING_MAIL_TO'])
            app.logger.addHandler(mail_handler)
        except Exception as e:
            app.logger.error(f'Mail Logging not working: {e}')

    csrf = CSRFProtect(app)

    limiter.init_app(app)

    return app
