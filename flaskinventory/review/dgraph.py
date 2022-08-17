from datetime import datetime
from string import ascii_letters
from flask import current_app
from flaskinventory import dgraph
from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.dgraph_types import (UID, NewID, Predicate, Scalar,
                                        GeoScalar, Variable, make_nquad, dict_to_nquad)
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.errors import InventoryDatabaseError


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
    for item in data:
        if 'Entry' in item['dgraph.type']:
            item['dgraph.type'].remove('Entry')
        if 'Resource' in item['dgraph.type']:
            item['dgraph.type'].remove('Resource')
    return data


def check_entry(uid=None, unique_name=None):

    if uid:
        uid = validate_uid(uid)
        if not uid:
            return False
        query = f'''{{ q(func: uid({uid})) @filter(has(dgraph.type))'''
    elif unique_name:
        query = f'''{{ q(func: eq(unique_name, "{unique_name}"))'''

    query += "{ uid unique_name dgraph.type entry_review_status entry_added { uid } channel { unique_name } } }"
    data = dgraph.query(query)

    if len(data['q']) == 0:
        return False

    return data['q'][0]


def accept_entry(uid, user):
    accepted = {'uid': UID(uid), 'entry_review_status': 'accepted',
                "reviewed_by": UID(user.id, facets={'timestamp': datetime.now()})}

    set_nquads = " \n ".join(dict_to_nquad(accepted))

    dgraph.upsert(None, set_nquads=set_nquads)


def reject_entry(uid, user):

    current_app.logger.debug(f'Rejecting entry: UID {uid}')

    uid = UID(uid)

    relationships = list(Schema.relationship_predicates().keys())
    query = []
    vars = {}

    for i, r in enumerate(relationships):
        var = Variable(ascii_letters[i], 'uid')
        query.append(f'{r}(func: has(dgraph.type)) @filter(uid_in({r}, {uid.query})) {{ {var.query} }}')
        vars[r] = var

    query = "\n".join(query)

    delete_predicates = ['dgraph.type', 'unique_name'] + relationships

    del_nquads = [make_nquad(uid, item, Scalar('*'))
                  for item in delete_predicates]
    for k, v in vars.items():
        del_nquads.append(make_nquad(v, k, uid))

    del_nquads = " \n ".join(del_nquads)

    rejected = {'uid': uid, 'entry_review_status': 'rejected', 'dgraph.type': 'Rejected',
                "reviewed_by": UID(user.id, facets={'timestamp': datetime.now()})}
    set_nquads = " \n ".join(dict_to_nquad(rejected))

    dgraph.upsert(query, del_nquads=del_nquads)
    dgraph.upsert(None, set_nquads=set_nquads)
