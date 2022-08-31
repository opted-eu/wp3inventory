from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from flaskinventory.flaskdgraph.customformfields import TomSelectMultipleField

class SimpleQuery(FlaskForm):

    entity = SelectField('Entity Type',
                         choices=[
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             ('Archive', 'Data Archive'),
                             ('Dataset', 'Dataset'),
                             ('Tool', 'Tool'),
                             ('Corpus', 'Corpus')
                             ],
                            validators=[DataRequired()],
                            name='dgraph.type')
    
    country = TomSelectMultipleField('Filter by Country')

    submit = SubmitField('Query')

    def get_field(self, field):
        return getattr(self, field, None)