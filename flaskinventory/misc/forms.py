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
def get_country_choices(opted=True):
    """ Helper function to get form choices 
        Queries for all countries and returns a list of tuples
        Filters countries by default according to OPTED scope
    """
    query_string = '''{ q(func: type("Country"), orderasc: name)'''
    if opted:
        query_string += ''' @filter(eq(opted_scope, true)) '''
    query_string += ''' { name uid } }'''
    countries = dgraph.query(query_string)
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    return c_choices

def get_subunit_choices():
    """ Helper function to get form choices 
        Queries for all subunits and returns a list of tuples
    """
    query_string = '''{ q(func: type("Subunit"), orderasc: name)  { name uid } }'''
    subunits = dgraph.query(query_string)
    su_choices = [(subunit.get('uid'), subunit.get('name'))
                 for subunit in subunits['q']]
    return su_choices