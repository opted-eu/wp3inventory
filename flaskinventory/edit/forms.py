from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField)


class RefreshWikidataForm(FlaskForm):

    
    uid = StringField('uid', render_kw={'readonly': True})
    submit = SubmitField('Refresh WikiData')
