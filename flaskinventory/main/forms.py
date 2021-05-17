from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user
from flaskinventory import dgraph


class HomeQueryForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=3), EqualTo('password')])

    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if dgraph.get_uid('username', username.data):
            raise ValidationError('That username is taken, please choose a different one.')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"'):
            raise ValidationError('That email is taken. Try to login!')