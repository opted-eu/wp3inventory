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


def make_mini_table(table_data):
    TableCls = create_table('Table')
    TableCls.classes = ['table']
    if 'date' in table_data[0].keys():
        TableCls.add_column('date', DateCol('Date'))
    if 'data_from' in table_data[0].keys():
        TableCls.add_column('data_from', ExternalURLCol('Data from', url_attr='data_from', attr='data_from'))
    for item in table_data[0].keys():
        if item == 'date' or item == 'data_from': continue
        TableCls.add_column(item, Col(item.replace("_", " ").title()))
    return TableCls(table_data)


def make_results_table(table_data):
    cols = list(table_data[0].keys())
    TableCls = create_table('Table')
    TableCls.classes = ['table']
    TableCls.allow_empty = True

    if 'founded' in cols:
        for item in table_data:
            if item.get('founded'):
                item['founded'] = item['founded'].year
            else:
                item['founded'] = 'NA'

    if 'published_date' in cols:
        for item in table_data:
            if item.get('published_date'):
                item['published_date'] = item['published_date'].year

    if 'authors' in cols:
        for item in table_data:
            if item.get('authors'):
                if item['authors'].startswith('['):
                    item['authors'] = item['authors'].replace('[', '').replace(']', '')

    if 'country' in cols:
        for item in table_data:
            if not item.get('country'):
                item['country'] = 'NA'

    if 'name' in cols:
        TableCls.add_column('name', LinkCol('Name', 'view.view_source', url_kwargs=dict(unique_name='unique_name'), attr_list='name'))
        cols.remove('name')
        cols.remove('unique_name')
    elif 'title' in cols:
        TableCls.add_column('title', LinkCol('Title', 'view.view_researchpaper', url_kwargs=dict(uid='uid'), attr_list='title'))
        cols.remove('title')

    cols.remove('uid')

    for item in cols:
        TableCls.add_column(item, Col(item.replace("_", " ").title()))
    return TableCls(table_data)

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
