from wtforms import StringField, SelectField, DateField, BooleanField, SubmitField, RadioField
from wtforms.fields.core import SelectMultipleField
from wtforms.fields.html5 import IntegerField

import datetime

class TomSelectMutlitpleField(SelectMultipleField):

    def pre_validate(self, form):
        pass


class TomSelectField(SelectField):

    def pre_validate(self, form):
        pass


class NullableDateField(DateField):
    """
    Native WTForms DateField throws error for empty dates.
    Let's fix this so that we could have DateField nullable.
    taken from: https://stackoverflow.com/questions/27766417/
    """

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist).strip()
            if date_str == '':
                self.data = None
                return
            try:
                self.data = datetime.datetime.strptime(
                    date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))

