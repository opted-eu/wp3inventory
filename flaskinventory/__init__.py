import os
from flask import Flask
from flask_login import LoginManager
from flaskinventory.dgraph import DGraph
from flask_mail import Mail
from flaskinventory.config import Config
import logging
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

dgraph = DGraph()

login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'

mail = Mail()

limiter = Limiter(key_func=get_remote_address)

def create_app(config_class=Config, config_json=None):
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)
    if config_json:
        app.config.from_json(config_json)
    else:
        app.config.from_object(config_class)
    
    from flaskinventory.users.routes import users
    from flaskinventory.inventory.routes import inventory
    from flaskinventory.records.routes import records
    from flaskinventory.main.routes import main
    from flaskinventory.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(inventory)
    app.register_blueprint(records)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    dgraph.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf = CSRFProtect(app)

    limiter.init_app(app)
    


    return app