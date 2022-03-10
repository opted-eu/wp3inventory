from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DateField, BooleanField,
                     IntegerField, SubmitField, TextAreaField, RadioField)
from wtforms.validators import DataRequired, Optional
from flask_login import current_user
from flaskinventory import dgraph
from flaskinventory.misc.forms import ownership_kind_choices
from flaskinventory.flaskdgraph.customformfields import TomSelectMutlitpleField, TomSelectField
from flaskinventory.main.model import Schema


class NewEntry(FlaskForm):
    name = StringField('Name of New Entity',
                       validators=[DataRequired()])

    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             ('Archive', 'Data Archive'),
                             ('Dataset', 'Dataset'),
                             #  ('ResearchPaper', 'Research Paper')
                         ],
                         validators=[DataRequired()])