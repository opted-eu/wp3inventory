from flaskinventory import login_manager
from flaskinventory.users.dgraph import User, check_user, check_user_by_email


@login_manager.user_loader
def load_user(user_id):
    if not user_id.startswith('0x'): return 
    if not check_user(user_id):
        return 
    return User(uid=user_id)