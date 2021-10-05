from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DateField, BooleanField,
                     IntegerField, SubmitField, TextAreaField, RadioField)
from wtforms.validators import DataRequired
from flask_login import current_user
from flaskinventory import dgraph
from flaskinventory.misc.forms import TomSelectMutlitpleField, TomSelectField


class NewEntry(FlaskForm):
    name = StringField('Name of New Entity',
                       validators=[DataRequired()])

    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             #  ('Archive', 'Data Archive'),
                             #  ('ResearchPaper', 'Research Paper')
                         ],
                         validators=[DataRequired()])


class NewOrganization(FlaskForm):
    uid = StringField('uid', render_kw={'readonly': True})
    name = StringField(
        'What is the legal or official name of the media organisation?', validators=[DataRequired()])
    other_names = StringField(
        'Does the organisation have any other names or aliases?')

    is_person = RadioField('Is the media organisation a person?', choices=[
                           ('n', 'No'), ('y', 'Yes')], validators=[DataRequired()])

    ownership_kind_choices = [('private ownership', 'Mainly private ownership'),
                              ('public ownership', 'Mainly public ownership'),
                              ('unknown', 'Unknown ownership')]
    ownership_kind = SelectField(
        'Is the media organization mainly privately owned or publicly owned?', choices=ownership_kind_choices, validators=[DataRequired()])

    country = SelectField(
        'In which country is the organisation located?', choices=[])

    employees = IntegerField(
        'How many employees does the news organization have?')

    publishes = TomSelectMutlitpleField(
        'Which news sources publishes the organisation (or person)?', choices=[])

    owns = TomSelectMutlitpleField(
        'Which other media organisations owns this organisation (or person)?', choices=[])

    entry_notes = TextAreaField(
        'Do you have any other notes on the entry that you just coded?')

    submit = SubmitField('Add New Media Organisation')

    def get_field(self, field):
        return getattr(self, field)
