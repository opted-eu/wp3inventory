from datetime import datetime
import secrets
from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, Markup)
from flask_login import login_user, current_user, logout_user, login_required
from flaskinventory import dgraph
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.users.forms import (InviteUserForm, RegistrationForm, LoginForm, UpdatePasswordForm,
                                        UpdateProfileForm, RequestResetForm, ResetPasswordForm,
                                        EditUserForm, AcceptInvitationForm)
from flaskinventory.users.utils import requires_access_level, make_users_table
from flaskinventory.users.emails import send_reset_email, send_invite_email, send_verification_email
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.dgraph import User, get_user_data, user_login, create_user, list_users, list_entries
from secrets import token_hex

users = Blueprint('users', __name__)


@users.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = {'email': form.email.data,
                    'pw': form.password.data}
        new_uid = create_user(new_user)
        user = User(uid=new_uid)
        send_verification_email(user)

        flash(
            f'Accounted created for {form.email.data} ({new_uid})! Please check your inbox and verify your email address!', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/register.html', title='Register', form=form)


@users.route('/register/verify/<token>')
def verify_email(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    user = User.verify_email_token(token)
    if user is None:
        flash('That is an invalid or expired token! Please contact us if you experiencing issues.', 'warning')
        return redirect(url_for('main.home'))

    flash('Email verified! You can now try to log in', 'success')
    return redirect(url_for('users.login'))

@users.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        if user_login(form.email.data, form.password.data):
            user = User(email=form.email.data)
            login_user(user, remember=form.remember.data)
            flash(f'You have been logged in', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('users.profile'))
        else:
            flash(Markup(f'Login unsuccessful. Please check username and password. Have you verified your email address? Do you need an account? <a href="{url_for("users.register")}" class="alert-link">You can register here</a>'), 'danger')
    return render_template('users/login.html', title='Login', form=form)


@users.route('/logout')
def logout():
    logout_user()
    flash(f'You have been logged out', 'info')
    return redirect(url_for('main.home'))


@users.route('/users/profile')
@login_required
def profile():
    user_role = USER_ROLES.dict_reverse[current_user.user_role]
    return render_template('users/profile.html', title='Profile', show_sidebar=True, user_role=user_role)


@users.route('/users/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        current_user.update_profile(form)
        flash(f'Your account has been updated', 'success')
        return redirect(url_for('users.profile'))
    elif request.method == 'GET':
        for field in form._fields:
            try:
                setattr(getattr(form, field), 'data', getattr(current_user, field))
            except AttributeError:
                continue
        # form.avatar_img.data = current_user.avatar_img
    return render_template('users/update_profile.html', title='Update Profile', form=form)


@users.route('/users/password/change', methods=['GET', 'POST'])
@login_required
def change_password():
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        current_user.change_password(form)
        flash(f'Your password has been changed', 'success')
        return redirect(url_for('users.profile'))

    return render_template('users/change_password.html', title='Change Password', form=form)


@users.route("/users/password/reset", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password', 'info')
        return redirect(url_for('users.login'))
    return render_template('users/reset_request.html', title='Reset Password', form=form)


@users.route("/users/password/reset/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = {'pw': form.password.data, 'pw_reset': False}
        new_uid = dgraph.update_entry(new_password, uid=user.id)

        flash(f'Password updated for {user.id}!', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/reset_token.html', title='Reset Password', form=form)

@users.route("/users/delete")
@login_required
def delete():
    if current_user.user_role == USER_ROLES.Admin:
        flash(f'Cannot delete admin accounts!', 'info')
        return redirect(url_for('users.profile'))
    mutation = {'account_status': 'deleted', 
                'account_status|timestamp': datetime.now().isoformat(),
                'display_name': 'Deleted User',
                'email': secrets.token_urlsafe(8),
                'pw': secrets.token_urlsafe(8),
                'user_orcid': '',
                'user_role': 1,
                'user_affiliation': '',
                'preference_emails': False}
    dgraph.update_entry(mutation, uid=current_user.id)
    logout_user()
    flash(f'Your account has been deleted!', 'info')
    return redirect(url_for('main.home'))

@users.route("/users/invitation/<token>", methods=['GET', 'POST'])
def accept_invitation(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))

    form = AcceptInvitationForm()
    if form.validate_on_submit():
        new_password = {'pw': form.password.data,
                        'pw_reset': False,
                        'date_joined': datetime.now(
                            datetime.timezone.utc).isoformat()}
        new_uid = dgraph.update_entry(new_password, uid=user.id)

        flash(f'Password updated for {user.email} ({user.id})!', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/accept_invitation.html', title='Accept Invitation', form=form)


@users.route('/users/invite', methods=['GET', 'POST'])
@login_required
def invite():
    form = InviteUserForm()
    if form.validate_on_submit():
        new_user = {'email': form.email.data,
                    'pw': token_hex(32)}
        new_uid = create_user(new_user, invited_by=current_user.id)
        NewUser = User(uid=new_uid)
        send_invite_email(NewUser)
        flash(
            f'Accounted created for {new_user["email"]} ({new_uid})!', 'success')
        return redirect(url_for('users.profile'))
    return render_template('users/invite.html', title='Invite New User', form=form)


@users.route('/users/admin')
@login_required
@requires_access_level(USER_ROLES.Admin)
def admin_view():
    user_list = list_users()
    if user_list:
        users_table = make_users_table(user_list)
    return render_template('users/admin.html', title='Manage Users', users=users_table)


@users.route('/users/<string:uid>/edit', methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Admin)
def edit_user(uid):
    editable_user = get_user_data(uid=uid)
    if editable_user is None:
        return abort(404)
    form = EditUserForm()
    if form.validate_on_submit():
        user_data = {}
        for k, v in form.data.items():
            if k in ['submit', 'csrf_token']:
                continue
            else:
                user_data[k] = v
        try:
            result = dgraph.update_entry(user_data, uid=uid)
        except Exception as e:
            return f'Database error {e}'
        flash(f'User {uid} has been updated', 'success')
        return redirect(url_for('users.admin_view'))
    elif request.method == 'GET':
        form.user_displayname.data = editable_user.get("user_displayname")
        form.user_role.data = editable_user.get("user_role")
    return render_template('users/update_user.html', title='Manage Users', user=editable_user, form=form)


@users.route('/users/<string:uid>/entries')
@login_required
def my_entries(uid):
    uid = validate_uid(uid)
    if not uid:
        return abort(404)
    if current_user.user_role > USER_ROLES.Contributor or current_user.id == uid:
        sources = list_entries(uid)
        if current_user.id == uid:
            title = 'My Entries'
        else:
            title = f'Entries of user <{uid}>' 
        if sources:
            return render_template('users/entries.html', 
                                    title=title, 
                                    show_sidebar=False, 
                                    drafts=sources[0].get('drafts'),
                                    pending=sources[0].get('pending'),
                                    accepted=sources[0].get('accepted'),
                                    rejected=sources[0].get('rejected'))
        else:
            return render_template('users/entries.html', 
                                    title=title, 
                                    show_sidebar=False, 
                                    drafts=None,
                                    pending=None,
                                    accepted=None)
    else:
        return abort(403)
        
