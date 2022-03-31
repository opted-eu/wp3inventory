from flask_table import create_table, Col, DateCol, LinkCol
from flask_table.html import element
from dateutil import parser as dateparser
from flask import url_for

class ExternalURLCol(Col):
    def __init__(self, name, url_attr, **kwargs):
        self.url_attr = url_attr
        super(ExternalURLCol, self).__init__(name, **kwargs)

    def td_contents(self, item, attr_list):
        url = self.from_attr_list(item, [self.url_attr])
        return element('a', {'href': url, 'target': '_blank'}, content="source")

class InternalURLCol(Col):
    def __init__(self, name, url_attr, **kwargs):
        self.url_attr = url_attr
        super(InternalURLCol, self).__init__(name, **kwargs)

    def td_contents(self, item, attr_list):
        text = self.from_attr_list(item, attr_list)
        url = self.from_attr_list(item, [self.url_attr])
        url = url_for('')
        return element('a', {'href': url}, content=text)


"""
Helper function to evaluate viewing permissions
Entries with "draft" or "pending" status can only be
viewed by the user who created the item or reviewers/admins
"""
def can_view(entry, user):
    if "entry_review_status" in entry.keys():
        if entry.get('entry_review_status') in ['pending', 'rejected']:
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
            return True
    else:
        return True
