from flaskinventory import login_manager
from flaskinventory.users.dgraph import User


@login_manager.user_loader
def load_user(user_id):
    return User(uid=user_id)
