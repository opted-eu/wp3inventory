from flask import current_app
from flaskinventory import dgraph
from flaskinventory.flaskdgraph import (UID, NewID, Predicate, Scalar,
                                        Geolocation, Variable, make_nquad, dict_to_nquad)


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
        query = f'''{{ q(func: uid({uid})) @filter(has(dgraph.type))'''
    elif unique_name:
        query = f'''{{ q(func: eq(unique_name, "{unique_name}"))'''

    query += "{ uid unique_name dgraph.type entry_review_status entry_added { uid } } }"
    data = dgraph.query(query)

    if len(data['q']) == 0:
        return False
    
    return data['q'][0]

def accept_entry(uid, user):
    accepted = {'uid': UID(uid), 'entry_review_status': 'accepted', "reviewed_by": UID(user.id)}

    set_nquads = " \n ".join(dict_to_nquad(accepted))

    dgraph.upsert(None, set_nquads=set_nquads)

def reject_entry(uid, user):

    current_app.logger.debug(f'Rejecting entry: UID {uid}')

    uid = UID(uid)
    related = Variable('v', 'uid')
    publishes = Variable('p', 'uid')
    owns = Variable('o', 'uid')
    query = f'''{{  related(func: type(Source)) @filter(uid_in(related, {uid.query()})) {{
			            {related.query()} }} 
                    publishes(func: type(Organization)) @filter(uid_in(publishes, {uid.query()})) {{
                        {publishes.query()} }}
                    owns(func: type(Organization)) @filter(uid_in(owns, {uid.query()})) {{
                        {owns.query()} }}
                }}'''

    delete_predicates = [Predicate('dgraph.type'), Predicate('unique_name'), Predicate('publishes'),
                        Predicate('owns'), Predicate('related')]
    
    del_nquads = [make_nquad(uid, item, Scalar('*')) for item in delete_predicates]
    del_nquads += [make_nquad(related, Predicate('related'), uid)]
    del_nquads += [make_nquad(publishes, Predicate('publishes'), uid)]
    del_nquads += [make_nquad(owns, Predicate('owns'), uid)]

    del_nquads = " \n ".join(del_nquads)
    

    rejected = {'uid': uid, 'entry_review_status': 'rejected', 'dgraph.type': 'Rejected', "reviewed_by": UID(user.id)}
    set_nquads = " \n ".join(dict_to_nquad(rejected))

    dgraph.upsert(query, del_nquads=del_nquads)
    dgraph.upsert(None, set_nquads=set_nquads)