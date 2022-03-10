from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired


class SimpleQuery(FlaskForm):
    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             ('Archive', 'Data Archive'),
                             ('Dataset', 'Dataset'),
                             ('ResearchPaper', 'Research Paper')],
                            validators=[DataRequired()])
    
    country = SelectField('Filter by Country')