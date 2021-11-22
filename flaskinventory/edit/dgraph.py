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