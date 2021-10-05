from flask import url_for, current_app, flash
from flask_login import current_user
from flaskinventory import dgraph
from flaskinventory.users.constants import USER_ROLES

def check_draft(draft, form):
    query_string = f"""{{ q(func: uid({draft}))  @filter(eq(entry_review_status, "draft")) {{ 
                            uid expand(_all_) {{ name unique_name uid }}
                            }} }}"""
    draft = dgraph.query(query_string)
    if len(draft['q']) > 0:
        draft = draft['q'][0]
        entry_added = draft.pop('entry_added')
        for key, value in draft['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                else:
                    choices = [(subval['uid'], subval['name']) for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                                'choices', choices)
                    
            setattr(getattr(form, key), 'data', value)
        # check permissions
        if current_user.uid != entry_added['uid']:
            if current_user.user_role >= USER_ROLES.Reviewer:
                flash("You are editing another user's draft", category='info')
            else:
                draft = None
                flash('You can only edit your own drafts!', category='warning')
    else:
        draft = None
    return draft
