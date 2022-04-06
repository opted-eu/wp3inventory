from flask_wtf import FlaskForm
from wtforms.fields import HiddenField, SubmitField, SelectField
from wtforms.validators import DataRequired


class ReviewFilter(FlaskForm):
    entity = SelectField('Filter by Entity Type',
                         choices=[
                             ('all', 'All'),
                             ('Source', 'News Source'),
                             ('Organization', 'Media Organization'),
                             ('Subunit', 'Subunit'),
                             ('Archive', 'Data Archive'),
                             ('Dataset', 'Dataset'),
                             ('Tool', 'Tool'),
                             ('Corpus', 'Corpus'),
                             ('ResearchPaper', 'Research Paper'),
                             ('Operation', 'Operation'),
                             ('FileFormat', 'File Format'),
                             ('MetaVar', 'Meta Variable'),
                             ('ConceptVar', 'Concept Variables'),
                             ('TextUnit', 'Text Unit')], validators=[DataRequired()]
                         )

    country = SelectField('Filter by Country')


class ReviewActions(FlaskForm):

    uid = HiddenField(label='UID', validators=[DataRequired()])
    accept = SubmitField('Accept')
    reject = SubmitField('Reject')
