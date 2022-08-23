from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from flaskinventory.flaskdgraph.customformfields import TomSelectMutlitpleField

class SimpleQuery(FlaskForm):

    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             ('Archive', 'Data Archive'),
                             ('Dataset', 'Dataset'),
                             ('Tool', 'Tool'),
                             ('Corpus', 'Corpus'),
                             ('ResearchPaper', 'Research Paper')],
                            validators=[DataRequired()],
                            name='dgraph.type')
    
    country = TomSelectMutlitpleField('Filter by Country')

    submit = SubmitField('Query')

    def get_field(self, field):
        return getattr(self, field, None)