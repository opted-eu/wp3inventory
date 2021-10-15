from flask import current_app
from flask_login import UserMixin
from flaskinventory import dgraph
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flaskinventory.users.constants import USER_ROLES
import datetime
import secrets

class User(UserMixin):
    
    id = None
    user_role = 0

    def __init__(self, **kwargs):
        if 'uid' or 'email' in kwargs.keys():
            self.get_user(**kwargs)

    def get_user(self, **kwargs):
        user_data = get_user_data(**kwargs)
        if user_data:
            for k, v in user_data.items():
                if k == 'uid':
                    self.id = v
                if '|' in k:
                    k = k.replace('|', '_')
                setattr(self, k, v)
        else:
            return None

    def update_profile(self, form_data):
        user_data = {}
        for k, v in form_data.data.items():
            if k in ['submit', 'csrf_token']: continue
            else: user_data[k] = v
        result = dgraph.update_entry(user_data, uid=self.id)
        if result:
            for k, v in user_data.items():
                setattr(self, k, v)
            return True
        else: return False

    def __repr__(self):
        return f'<DGraph User.uid {self.id}>'

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        dgraph.update_entry({'pw_reset': s.dumps({'user_id': self.id}).decode('utf-8'),
                                         'pw_reset|used': False}, uid=self.id)
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
        user = User(uid=user_id)
        if user.pw_reset_used:
            return None
        elif user.pw_reset != token:
            return None
        else:
            dgraph.update_entry({'pw_reset|used': True}, uid=user_id)
            return user

from flaskinventory import login_manager
@login_manager.user_loader
def load_user(user_id):
    if not user_id.startswith('0x'): return 
    if not check_user(user_id):
        return 
    return User(uid=user_id)


def get_user_data(**kwargs):

    uid = kwargs.get('uid', None)
    email = kwargs.get('email', None)

    if uid:
        query_func = f'{{ q(func: uid({uid}))'
    elif email:
        query_func = f'{{ q(func: eq(email, "{email}"))'
    else:
        raise ValueError()

    query_fields = f'{{ uid email pw_reset @facets user_displayname user_orcid date_joined user_role user_affiliation }} }}'
    query_string = query_func + query_fields
    data = dgraph.query(query_string)
    if len(data['q']) == 0:
        return None
    data = data['q'][0]
    return data

def check_user(uid):

    query_string = f'''{{ user(func: uid({uid})) @filter(type("User")) {{ uid }} }}'''
    data = dgraph.query(query_string)
    if len(data['user']) == 0:
        return None
    return data['user'][0]['uid']

def check_user_by_email(email):
    query_string = f'''{{ user(func: eq(email, "{email}")) @filter(type("User")) {{ uid }} }}'''
    data = dgraph.query(query_string)
    if len(data['user']) == 0:
        return None
    return data['user'][0]['uid']


def user_login(email, pw):
    query_string = f'{{login_attempt(func: eq(email, "{email}")) {{ checkpwd(pw, {pw}) }} }}'
    result = dgraph.query(query_string)
    if len(result['login_attempt']) == 0:
        return False
    else:
        return result['login_attempt'][0]['checkpwd(pw)']

def create_user(user_data, invited_by=None):
    if type(user_data) is not dict:
        raise TypeError()


    user_data['uid'] = '_:newuser'
    user_data['dgraph.type'] = 'User'
    user_data['user_role'] = USER_ROLES.Contributor
    user_data['user_displayname'] = secrets.token_urlsafe(6)
    user_data['date_joined'] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()
    user_data['account_status'] = 'active'

    if invited_by:
        user_data['invited_by'] = {'uid': invited_by,
                                    'invited_by|date': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        user_data['account_status'] = 'invited'
        

    response = dgraph.mutation(user_data)

    if response:
        return response.uids['newuser']
    else:
        return False

def list_users():
    data = dgraph.query('{ q(func: type("User")) { uid expand(_all_) } }')
    if len(data['q']) == 0:
        return False
    return data['q']

def list_entries(user, onlydrafts=False):
    query_string = f"""{{ q(func: uid({user})) {{
        drafts: ~entry_added @facets(orderdesc: timestamp) @filter(eq(entry_review_status, "draft"))
        {{ uid unique_name name dgraph.type entry_review_status }} 
        """

    if onlydrafts:
        query_string += '} }'
    else:
        query_string += f"""
            pending: ~entry_added @facets(orderdesc: timestamp) @filter(eq(entry_review_status, "pending"))
            {{ uid unique_name name dgraph.type entry_review_status }} 
            accepted: ~entry_added @facets(orderdesc: timestamp) @filter(eq(entry_review_status, "accepted"))
            {{ uid unique_name name dgraph.type entry_review_status }}
            }} }}
            """

    data = dgraph.query(query_string)

    if len(data['q']) == 0:
        return False
    return data['q']
