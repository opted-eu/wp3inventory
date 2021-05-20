from flask import current_app
from flask_login import UserMixin
from flaskinventory import dgraph, login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User(uid=user_id)

class User(UserMixin):
    
    id = None

    def __init__(self, **kwargs):
        if 'uid' or 'email' in kwargs.keys():
            self.get_user(**kwargs)

    def get_user(self, **kwargs):
        user_data = dgraph.get_user(**kwargs)
        if user_data:
            for k, v in user_data.items():
                if k == 'uid':
                    self.id = v
                setattr(self, k, v)

    def update_profile(self, form_data):
        user_data = {}
        for k, v in form_data.data.items():
            if k in ['submit', 'csrf_token']: continue
            else: user_data[k] = v
        result = dgraph.update_entry(self.id, user_data)
        if result:
            for k, v in user_data.items():
                setattr(self, k, v)
            return True
        else: return False

    def __repr__(self):
        return f'<DGraph User.uid {self.id}>'

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')
    
    def get_invite_token(self, expires_days=7):
        expires_sec = expires_days * 24 * 60 * 60 
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User(uid=user_id)