from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user
from flaskinventory import dgraph


class RegistrationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=3), EqualTo('password')])

    submit = SubmitField('Request Account')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"'):
            raise ValidationError('That email is taken. Try to login!')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    remember = BooleanField('Remember Me')

    submit = SubmitField('Login')



class UpdateProfileForm(FlaskForm):
    user_displayname = StringField('Display Name',
                        validators=[Length(min=2, max=40)])
    user_affiliation = StringField('Affiliation', 
                        validators=[Length(max=(60))])
    user_orcid = StringField('ORCID', 
                        validators=[Length(min=12)])

    submit = SubmitField('Update')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()]) 
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"') is None:
            raise ValidationError('There is no account with that email. Please register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=3), EqualTo('password')])

    submit = SubmitField('Reset Password')