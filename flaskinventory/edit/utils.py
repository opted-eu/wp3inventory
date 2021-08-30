from flaskinventory.add.external import geocode
from flaskinventory import dgraph

def sanitize_edit_org(data):

    if 'uid' not in data.keys():
        raise TypeError

    organization = {'uid': data.get('uid'),
                'unique_name': data.get('unique_name'),
                'name': data.get('name'),
                'founded': data.get('founded').isoformat(),
                'is_person': data.get('is_person'),
                'ownership_kind': data.get('ownership_kind'),
                'address_string': data.get('address_string'),
                'employees': data.get('employees'),
                'entry_notes': data.get('entry_notes')                
                }

    try:
        organization['wikidataID'] = int(data.get('wikidataID').lower().replace('q', ''))
    except:
        pass
    try:
        organization['other_names'] = [item.strip() for item in data['other_names'].split(',')]
    except:
        pass
    try:
        address_geo = geocode(data.get('address_string'))
        organization["address_geo"] = {'type': 'Point', 'coordinates': [
                float(address_geo.get('lon')), float(address_geo.get('lat'))]}
    except:
        address_geo = None

    res = dgraph.update_entry(organization)
    if res == False:
        raise Exception('Could not run mutation')

    # update country
    del_country = {'uid': data.get('uid'), 'country': None}
    dgraph.delete(del_country)
    new_country = {'uid': data.get('uid'), 'country': {'uid': data.get('country')}}
    dgraph.update_entry(new_country)

    del_publishes = {'uid': data.get('uid'), 'publishes': None}
    dgraph.delete(del_publishes)
    for item in data.get('publishes_unique_name').split(','):
        if item.strip() == "": continue
        query = f'{{ v as var(func: eq(unique_name, "{item.strip()}")) }}'
        nquads = f'<{data.get("uid")}> <publishes> uid(v) .'
        res = dgraph.upsert(query, nquads)
        if res == False:
            raise Exception('Could not run mutation')

    del_owns = {'uid': data.get('uid'), 'owns': None}
    dgraph.delete(del_owns)
    for item in data.get('owns_unique_name').split(','):
        if item.strip() == "": continue
        query = f'{{ v as var(func: eq(unique_name, "{item.strip()}")) }}'
        nquads = f'<{data.get("uid")}> <owns> uid(v) .'
        res = dgraph.upsert(query, set_nquads=nquads)
        if res == False:
            raise Exception('Could not run mutation')






    