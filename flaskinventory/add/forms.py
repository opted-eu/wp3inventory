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
                              ('Archive', 'Data Archive'),
                             #  ('ResearchPaper', 'Research Paper')
                         ],
                         validators=[DataRequired()])


class NewOrganization(FlaskForm):
    uid = StringField('uid', render_kw={'readonly': True})
    name = StringField(
        'What is the legal or official name of the media organisation?', validators=[DataRequired()],
        render_kw={'placeholder': 'e.g. "The Big Media Corp."'})
    other_names = StringField(
        'Does the organisation have any other names or common abbreviations?',
        render_kw={'placeholder': 'Separate by comma'})

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
        'How many employees does the news organization have?',
        render_kw={'placeholder': 'Most recent figure as plain number'})

    publishes = TomSelectMutlitpleField(
        'Which news sources publishes the organisation (or person)?', choices=[],
        render_kw={'placeholder': 'Type to search existing news sources and add multiple...'})

    owns = TomSelectMutlitpleField(
        'Which other media organisations owns this organisation (or person)?', choices=[],
        render_kw={'placeholder': 'Type to search existing organisations and add multiple...'})

    entry_notes = TextAreaField(
        'Do you have any other notes on the entry that you just coded?')

    submit = SubmitField('Add New Media Organisation')

    def get_field(self, field):
        return getattr(self, field)


class NewArchive(FlaskForm):
    uid = StringField('uid', render_kw={'readonly': True})
    name = StringField(
        'What is the name of the full text archive?', validators=[DataRequired()],
        render_kw={'placeholder': 'e.g. "The Web Archive"'})
    other_names = StringField(
        'Does the archive have any other names or common abbreviations?',
        render_kw={'placeholder': 'Separate by comma'})

    access = RadioField('Is the archive freely accessible or has some sort of restriction?', choices=[
                           ('free', 'Free'), ('restricted', 'Restricted')], validators=[DataRequired()])

    url = StringField('Please specify the URL to the full text archive', validators=[DataRequired()],
                        render_kw={'placeholder': 'e.g. "http://www.archive.org"'})

    sources_included = TomSelectMutlitpleField(
        'Which news sources are included in the full text archive?', choices=[],
        render_kw={'placeholder': 'Type to search existing entries and add multiple...'})

    description = TextAreaField(
        'Can you briefly describe the archive?',
        render_kw={'placeholder': 'You can also paste their official self-description'})

    entry_notes = TextAreaField(
        'Do you have any other notes on the entry that you just coded?')

    submit = SubmitField('Add New Full Text Archive')

    def get_field(self, field):
        return getattr(self, field)



class NewCountry(FlaskForm):
    uid = StringField('uid', render_kw={'readonly': True})
    name = StringField('Name', validators=[DataRequired()])
    other_names = StringField('Other Names',
        render_kw={'placeholder': 'Separate by comma'})

    country_code = StringField('Country Code', validators=[DataRequired()],
                        render_kw={'placeholder': 'e.g. at, de, tw'})

    submit = SubmitField('Add New Country')

    def get_field(self, field):
        return getattr(self, field)