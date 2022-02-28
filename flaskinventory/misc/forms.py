from wtforms import SelectField
from wtforms.fields.core import SelectMultipleField
from flaskinventory import dgraph


class TomSelectMutlitpleField(SelectMultipleField):

    def pre_validate(self, form):
        pass


class TomSelectField(SelectField):

    def pre_validate(self, form):
        pass

# cache this function


def get_country_choices(opted=True, multinational=False) -> list:
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


publication_kind_choices = [('newspaper', 'Newspaper / News Site'), ('news agency', 'News Agency'), ('magazine', 'Magazine'), ('tv show', 'TV Show / TV Channel'), (
    'radio show', 'Radio Show / Radio Channel'), ('podcast', 'Podcast'), ('news blog', 'News Blog'), ('alternative media', 'Alternative Media')]


publication_kind_dict = {key: val for (key, val) in publication_kind_choices}


topical_focus_choices = [("politics", "Politics"),
                         ("society", "Society & Panorama"),
                         ("economy", "Business, Economy, Finance & Stocks"),
                         ("religion", "Religion"),
                         ("science", "Science & Technology"),
                         ("media", "Media"),
                         ("environment", "Environment"),
                         ("education", "Education")]

topical_focus_dict = {key: val for (key, val) in topical_focus_choices}


ownership_kind_choices = [('none', 'Missing!'),
                          ('public ownership', 'Mainly public ownership'),
                          ('private ownership', 'Mainly private Ownership'),
                          ('political party', 'Political Party'),
                          ('unknown', 'Unknown Ownership')]

ownership_kind_dict = {key: val for (key, val) in ownership_kind_choices}

