from flask_table import create_table, Col, DateCol, LinkCol
from flask_table.html import element
from dateutil import parser as dateparser
from flask import url_for

def database_check_table(table_data):
    cols = list(table_data[0].keys())
    TableCls = create_table('Table')
    TableCls.classes = ['table', 'table-hover']

    if 'name' in cols:
        TableCls.add_column('name', LinkCol('Name', 'inventory.view_source', url_kwargs=dict(unique_name='unique_name'), attr_list='name'))
        cols.remove('name')
        cols.remove('unique_name')


    cols.remove('uid')

    for item in cols:
        TableCls.add_column(item, Col(item.replace("_", " ").title()))
    return TableCls(table_data)