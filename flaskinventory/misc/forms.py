from flaskinventory import dgraph


# cache this function
def get_country_choices(opted=True, multinational=False, addblank=False) -> list:
    """ Helper function to get form choices 
        Queries for all countries and returns a list of tuples
        [(<uid>, 'Country Name'), ...]
        Filters countries by default according to OPTED scope
    """
    query_string = '''{ q(func: type("Country"), orderasc: name)'''
    if opted:
        query_string += ''' @filter(eq(opted_scope, true)) '''
    query_string += ''' { name uid } '''
    if multinational:
        query_string += ''' m(func: type("Multinational"), orderasc: name) { name uid } '''
    query_string += '}'
    countries = dgraph.query(query_string)
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    if multinational:
        c_choices += [(multi.get('uid'), multi.get('name'))
                      for multi in countries['m']]
    if addblank:
        c_choices.insert(0, ('', ''))
    return c_choices


def get_subunit_choices():
    """ Helper function to get form choices 
        Queries for all subunits and returns a list of tuples
    """
    query_string = '''{ q(func: type("Subunit"), orderasc: name)  { name uid country { name } } }'''
    subunits = dgraph.query(query_string)
    su_choices = [(subunit.get('uid'), f"{subunit.get('name')} [{subunit['country'][0]['name'] if subunit.get('country') else 'MISSING'}]")
                  for subunit in subunits['q']]
    return su_choices
