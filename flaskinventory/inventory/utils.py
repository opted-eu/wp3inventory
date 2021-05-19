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
    if 'datafrom' in table_data[0].keys():
        TableCls.add_column('datafrom', ExternalURLCol('Datafrom', url_attr='datafrom', attr='datafrom'))
    for item in table_data[0].keys():
        if item == 'date' or item == 'datafrom': continue
        TableCls.add_column(item, Col(item.replace("_", " ").title()))
    return TableCls(table_data)


def make_results_table(table_data):
    cols = list(table_data[0].keys())
    TableCls = create_table('Table')
    TableCls.classes = ['table']

    if 'founded' in cols:
        for item in table_data:
            if item.get('founded'):
                item['founded'] = item['founded'].year

    if 'published_date' in cols:
        for item in table_data:
            if item.get('published_date'):
                item['published_date'] = item['published_date'].year

    if 'authors' in cols:
        for item in table_data:
            if item.get('authors'):
                if item['authors'].startswith('['):
                    item['authors'] = item['authors'].replace('[', '').replace(']', '')

    if 'name' in cols:
        TableCls.add_column('name', LinkCol('Name', 'inventory.view_source', url_kwargs=dict(unique_name='unique_name'), attr_list='name'))
        cols.remove('name')
        cols.remove('unique_name')
    elif 'title' in cols:
        TableCls.add_column('title', LinkCol('Title', 'inventory.view_researchpaper', url_kwargs=dict(uid='uid'), attr_list='title'))
        cols.remove('title')

    cols.remove('uid')

    for item in cols:
        TableCls.add_column(item, Col(item.replace("_", " ").title()))
    return TableCls(table_data)