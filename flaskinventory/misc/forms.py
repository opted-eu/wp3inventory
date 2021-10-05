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
def get_country_choices():
    countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])
    return c_choices