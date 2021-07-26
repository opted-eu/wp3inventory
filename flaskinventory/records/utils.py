from flask_table import create_table, Col, DateCol, LinkCol
from flask_table.html import element
from dateutil import parser as dateparser
from flask import url_for, current_app
from flaskinventory.records.external import geocode
from flaskinventory import dgraph

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


def sanitize_edit_org(data):

    if 'uid' not in data.keys():
        raise TypeError

    organization = {'uid': data.get('uid'),
                'unique_name': data.get('unique_name'),
                'name': data.get('name'),
                'founded': data.get('founded').isoformat(),
                'is_person': data.get('is_person'),
                'ownership_kind': data.get('ownership_kind'),
                'country': {'uid': data.get('country')},
                'address_string': data.get('address_string'),
                'employees': data.get('employees'),
                'entry_notes': data.get('entry_notes')                
                }

    try:
        organization['wikidataID'] = int(data.get('wikidataID').lower().replace('q', ''))
    except:
        pass
    organization['other_names'] = [item.strip() for item in data['other_names'].split(',')]
    try:
        address_geo = geocode(data.get('address_string'))
        organization["address_geo"] = {'type': 'Point', 'coordinates': [
                float(address_geo.get('lon')), float(address_geo.get('lat'))]}
    except:
        address_geo = None

    res = dgraph.update_entry(organization)
    if res == False:
        raise Exception('Could not run mutation')

    for item in data.get('publishes_unique_name').split(','):
        if item.strip() == "": continue
        query = f'{{ v as var(func: eq(unique_name, "{item.strip()}")) }}'
        nquads = f'<{data.get("uid")}> <publishes> uid(v) .'
        res = dgraph.upsert(query, nquads)
        if res == False:
            raise Exception('Could not run mutation')

        
    for item in data.get('owns_unique_name').split(','):
        if item.strip() == "": continue
        query = f'{{ v as var(func: eq(unique_name, "{item.strip()}")) }}'
        nquads = f'<{data.get("uid")}> <owns> uid(v) .'
        res = dgraph.upsert(query, nquads)
        if res == False:
            raise Exception('Could not run mutation')






    