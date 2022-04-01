from flaskinventory import dgraph

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