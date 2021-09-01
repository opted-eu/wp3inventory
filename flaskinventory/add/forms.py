from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, SubmitField
from wtforms.validators import DataRequired
from flask_login import current_user
from flaskinventory import dgraph


class NewEntry(FlaskForm):
    name = StringField('Name',
                           validators=[DataRequired()])
    
    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                            #  ('Organization', 'Media Organization'),
                            #  ('Archive', 'Data Archive'),
                            #  ('ResearchPaper', 'Research Paper')
                             ],
                            validators=[DataRequired()])



