
def can_edit(entry, user):
    if "entry_review_status" in entry.keys():
        if entry.get('entry_review_status') in ['pending', 'accepted']:
            if user.is_authenticated:
                if user.user_role > 1 or entry.get('entry_added').get('uid') == user.id:
                    return True
                else:
                    return False
            else: 
                return False
        elif entry.get('entry_review_status') == 'draft':
            if user.is_authenticated:
                if user.user_role > 2 or entry.get('entry_added').get('uid') == user.id:
                    return True
                else: 
                    return False
            else: 
                return False
        else:
            return False
    else:
        return True
