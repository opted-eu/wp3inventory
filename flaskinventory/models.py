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
        if 'uid' or 'email' or 'username' in kwargs.keys():
            self.get_user(**kwargs)

    def get_user(self, **kwargs):
        user_data = dgraph.get_user(**kwargs)
        if user_data:
            self.id = user_data['uid']
            self.username = user_data['username']
            self.email = user_data['email']
            self.avatar_img = user_data['avatar_img']
            self.date_joined = user_data['date_joined']

    def update_profile(self, form_data):
        user_data = {}
        user_data['username'] = form_data.username.data
        user_data['email'] = form_data.email.data
        if form_data.avatar_img.data:
            user_data['avatar_img'] = form_data.avatar_img.data.filename
        result = dgraph.update_entry(self.id, user_data)
        if result:
            if 'username' in user_data.keys():
                self.username = user_data['username']
            if 'email' in user_data.keys():
                self.email = user_data['email']
            if 'avatar_img' in user_data.keys():
                self.avatar_img = user_data['avatar_img']
            return True
        else: return False

    def __repr__(self):
        return f'<DGraph User.uid {self.id}>'

    def get_reset_token(self, expires_sec=1800):
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