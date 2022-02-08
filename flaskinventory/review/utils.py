
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.review.forms import ReviewActions

def create_review_actions(user, uid, review_status):
    if review_status != 'pending': return None
    if user.user_role > USER_ROLES.Contributor:
            review_actions = ReviewActions()
            review_actions.uid.data = uid
    else:
        review_actions = None
    
    return review_actions