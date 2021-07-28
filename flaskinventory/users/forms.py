from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user
from flaskinventory import dgraph
from flaskinventory.users.constants import USER_ROLES


class RegistrationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])

    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=6), EqualTo('password')])

    submit = SubmitField('Create Account')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"'):
            raise ValidationError('That email is taken. Try to login!')


class InviteUserForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    submit = SubmitField('Invite User')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"'):
            raise ValidationError('That email is taken. User has been invited already!')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    remember = BooleanField('Remember Me')

    submit = SubmitField('Login')


class UpdateProfileForm(FlaskForm):
    user_displayname = StringField('Display Name',
                                   validators=[Length(min=2, max=40)])
    user_affiliation = StringField('Affiliation',
                                   validators=[Length(max=(60))])
    user_orcid = StringField('ORCID',
                             validators=[Length(max=20)])

    submit = SubmitField('Update')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        if dgraph.get_uid('email', f'"{email.data}"') is None:
            raise ValidationError(
                'There is no account with that email. Please register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=3), EqualTo('password')])

    submit = SubmitField('Reset Password')

class AcceptInvitationForm(FlaskForm):
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=3)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), Length(min=3), EqualTo('password')])

    submit = SubmitField('Set Password')

class EditUserForm(FlaskForm):
    user_displayname = StringField('Display Name',
                                   validators=[Length(min=2, max=40)])

    user_role = SelectField(
        'User Role', choices=USER_ROLES.list_of_tuples_b)

    submit = SubmitField('Update')
