from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
from flask_login import current_user
from flaskinventory import dgraph


class NewEntry(FlaskForm):
    name = StringField('Name',
                           validators=[DataRequired()])
    
    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'Journalistic Source'),
                            #  ('Organization', 'Media Organization'),
                            #  ('Archive', 'Data Archive'),
                            #  ('ResearchPaper', 'Research Paper')
                             ],
                            validators=[DataRequired()])