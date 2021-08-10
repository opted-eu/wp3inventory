from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, SubmitField
from wtforms.validators import DataRequired
from flask_login import current_user
from flaskinventory import dgraph

ownership_kind_choices = [('public ownership', 'Mainly public ownership'),
                      ('private ownership', 'Mainly private Ownership'), 
                      ('unknown', 'Unknown Ownership'), 
                      ('none', 'Missing!')]


class OrganizationForm(FlaskForm):

    uid = StringField('uid', render_kw={'readonly': True})

    unique_name = StringField('Unique Name', 
                                validators=[DataRequired()])
    
    name = StringField('Name', validators=[DataRequired()])

    other_names = StringField('Other Names')

    wikidataID = StringField('Wikidata ID')

    founded = DateField('Founded', render_kw={'type': 'date'})

    is_person = BooleanField('Is a person')

    ownership_kind = SelectField('Type of Organization', choices=ownership_kind_choices, validators=[DataRequired()])

    country = SelectField('Country')

    address_string = StringField('Address')

    address_geo = StringField('Address Geodata', render_kw={'readonly': True})

    employees = StringField('Number of employees')

    publishes_unique_name = StringField('Publishes')
    publishes = StringField('Publishes (uid)', render_kw={'readonly': True})

    owns_unique_name = StringField('Owns')
    owns = StringField('Owns (uid)', render_kw={'readonly': True})

    entry_added = StringField('Entry Added by', render_kw={'readonly': True})
    entry_edit_history = StringField('Entry Edit History', render_kw={'readonly': True})
    entry_review_status = StringField('Entry Review Status', render_kw={'readonly': True})
    entry_notes = StringField('Entry Comments')

    submit = SubmitField('Edit')


