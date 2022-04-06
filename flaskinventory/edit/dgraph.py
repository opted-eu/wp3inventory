from flaskinventory import dgraph
from flask import current_app
from flaskinventory.flaskdgraph.dgraph_types import UID, Variable, Scalar, make_nquad, dict_to_nquad

def get_entry(unique_name=None, uid=None):
    if unique_name:
        query_string = f'''{{ q(func: eq(unique_name, "{unique_name}"))'''
    elif uid:
        query_string = f'''{{ q(func: uid({uid}))'''
    else:
        return False
    query_string += '{ uid expand(_all_) { name unique_name uid user_displayname } } }'

    result = dgraph.query(query_string)
    return result

def get_audience(uid):
    query_string = f'''{{ q(func: uid({uid})) {{ 
                    uid unique_name audience_size @facets 
                    channel {{ unique_name }} }} }}'''
    
    result = dgraph.query(query_string)

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
    related = Variable('v', 'uid')
    publishes = Variable('p', 'uid')
    owns = Variable('o', 'uid')
    source_included = Variable('i', 'uid') 
    query = f'''{{  related(func: type(Source)) @filter(uid_in(related, {uid.query})) {{
			            {related.query} }} 
                    publishes(func: type(Organization)) @filter(uid_in(publishes, {uid.query})) {{
                        {publishes.query} }}
                    owns(func: type(Organization)) @filter(uid_in(owns, {uid.query})) {{
                        {owns.query} }}
                    included(func: has(dgraph.type)) @filter(uid_in(sources_inclued, {uid.query})) {{
                        {source_included.query}
                    }}
                    
                }}'''

    delete_predicates = ['dgraph.type', 'unique_name', 'publishes',
                         'owns', 'related']

    del_nquads = [make_nquad(uid, item, Scalar('*'))
                  for item in delete_predicates]
    del_nquads += [make_nquad(related, 'related', uid)]
    del_nquads += [make_nquad(publishes, 'publishes', uid)]
    del_nquads += [make_nquad(owns, 'owns', uid)]
    del_nquads += [make_nquad(source_included, 'sources_included', uid)]

    del_nquads = " \n ".join(del_nquads)

    deleted = {'uid': uid, 'entry_review_status': 'deleted'}
    set_nquads = " \n ".join(dict_to_nquad(deleted))

    dgraph.upsert(query, del_nquads=del_nquads)
    dgraph.upsert(None, set_nquads=set_nquads)

    final_delete = f'{uid.nquad} * * .'

    dgraph.upsert(None, del_nquads=final_delete)
