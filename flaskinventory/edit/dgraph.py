from string import ascii_letters

from flaskinventory import dgraph
from flask import current_app
from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.dgraph_types import UID, Variable, Scalar, make_nquad, dict_to_nquad

def get_entry(unique_name=None, uid=None):
    query_string = 'query get_entry($query: string) {'
    if unique_name:
        query_string += 'q(func: eq(unique_name, $query))'
        variables = {'$query': unique_name}
    elif uid:
        query_string += 'q(func: uid($query))'
        variables = {'$query': uid}
    else:
        return False
    query_string += '{ uid expand(_all_) { name unique_name uid user_displayname } } }'

    result = dgraph.query(query_string, variables=variables)
    return result

def get_audience(uid):
    query_string = '''
    query get_audience($query: string) {
        q(func: uid($query)) { 
            uid unique_name audience_size @facets 
            channel { unique_name } 
            } 
        }'''
    
    result = dgraph.query(query_string, variables={"$query": uid})

    data = result['q'][0]

    rows = []
    # convert to list of dicts
    if 'audience_size' not in data.keys():
        cols = ['date']
        if data['channel']['unique_name'] == 'print':
            cols += ['copies_sold', 'data_from']
        elif data['channel']['unique_name'] == 'facebook':
            cols.append('likes')
        else:
            return False
    else:
        keys = [key for key in data.keys() if key.startswith('audience_size|')]
        for i, item in enumerate(data['audience_size']):
            d = {'date': item}
            for key in keys:
                d[key.replace('audience_size|', '')] = data[key][str(i)]
            rows.append(d)

        cols = ['date'] + [key.replace('audience_size|', '') for key in keys]
    
    output = {'cols': cols, 'rows': rows}

    return output



def draft_delete(uid):

    current_app.logger.debug(f'Deleting draft: UID {uid}')

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

    deleted = {'uid': uid, 'entry_review_status': 'deleted'}
    set_nquads = " \n ".join(dict_to_nquad(deleted))

    dgraph.upsert(query, del_nquads=del_nquads)
    dgraph.upsert(None, set_nquads=set_nquads)

    final_delete = f'{uid.nquad} * * .'

    dgraph.upsert(None, del_nquads=final_delete)
