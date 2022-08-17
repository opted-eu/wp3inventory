import logging
import json

from flask import Flask
from .config import create_filehandler, create_slackhandler
from flaskinventory.config import Config

#### Load Extensions ####
# Login Extension
from flask_login import LoginManager, AnonymousUserMixin
# E-Mail Extension
from flask_mail import Mail
# Forms Extension
from flask_wtf.csrf import CSRFProtect
# Rate Limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# Markdown Rendering
from flaskext.markdown import Markdown
from markdown.extensions.toc import TocExtension

# Custom Dgraph Extension
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
    # assert versions
    import wtforms
    assert wtforms.__version__.startswith('3.'), 'WTForms Version 3.X.X is required!'

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
    
    if app.config.get('SLACK_LOGGING_ENABLED'):
        try:
            slack_handler = create_slackhandler(app.config.get('SLACK_WEBHOOK'))
            app.logger.addHandler(slack_handler)
            app.logger.error('Initialized Slack Logging!')
        except Exception as e:
            app.logger.error(f'Slack Logging not working: {e}')

    app.config['APP_VERSION'] = "1.0.3"

    from flaskinventory.users.routes import users
    from flaskinventory.view.routes import view
    from flaskinventory.add.routes import add
    from flaskinventory.edit.routes import edit
    from flaskinventory.review.routes import review
    from flaskinventory.endpoints.routes import endpoint
    from flaskinventory.main.routes import main
    from flaskinventory.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(view)
    app.register_blueprint(add)
    app.register_blueprint(edit)
    app.register_blueprint(review)
    app.register_blueprint(endpoint)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    dgraph.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    csrf = CSRFProtect(app)

    limiter.init_app(app)

    Markdown(app, extensions=[TocExtension(baselevel=3, anchorlink=True), 'fenced_code'])

    return app
