from flask import current_app
from flaskinventory import dgraph



def get_overview(dgraphtype, country=None, user=None):
    if dgraphtype == 'all':
        query_head = f'''{{ q(func: has(dgraph.type)) @filter(eq(entry_review_status, "pending") '''
    else:
        query_head = f'''{{ q(func: type({dgraphtype})) @filter(eq(entry_review_status, "pending") '''
    
    query_fields = f''' uid name unique_name dgraph.type 
                        entry_added @facets(timestamp) {{ uid user_displayname }}
                        country {{ uid unique_name name }} 
                        channel {{ uid unique_name name }} '''

    filt_string = ''
    if country:
        if country != 'all':
            filt_string += f''' AND uid_in(country, {country}) '''

    if user:
        if user != 'any':
            filt_string += f''' AND uid_in(entry_added, {user})'''

    filt_string += ')'
    

    query = f'{query_head} {filt_string} {{ {query_fields} }} }}'

    data = dgraph.query(query)

    if len(data['q']) == 0:
        return False

    data = data['q']
    return data

def check_entry(uid=None, unique_name=None):

    if uid:
        query = f'''{{ q(func: uid({uid}))'''
    elif unique_name:
        query = f'''{{ q(func: eq(unique_name, "{unique_name}"))'''

    query += "{ uid unique_name dgraph.type entry_review_status entry_added { uid } } }"
    data = dgraph.query(query)

    if len(data['q']) == 0:
        return False
    
    return data['q'][0]

def accept_entry(uid):
    accepted = {'entry_review_status': 'accepted'}

    dgraph.update_entry(accepted, uid=uid)

def reject_entry(uid):
    del_nquads = f'''<{uid}> <dgraph.type> * .
                        <{uid}> <unique_name> * .
                        <{uid}> <publishes> * .
                        <{uid}> <owns> * .'''
    query = None
    dgraph.upsert(query, del_nquads=del_nquads)

    rejected = {'entry_review_status': 'rejected', 'dgraph.type': 'Rejected'}

    dgraph.update_entry(rejected, uid=uid)

