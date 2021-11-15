def escape_query(query):
    # Dgraph query strings have some weaknesses 
    # towards certain special characters
    # for term matching and regex these characters
    # can simply be removed
    return query.replace('/', '').replace('"', '')
