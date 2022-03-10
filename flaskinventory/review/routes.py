from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, current_app)
from flask_login import login_required, current_user
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.review.forms import ReviewFilter
from flaskinventory.review.dgraph import get_overview, accept_entry, reject_entry
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.utils import requires_access_level

review = Blueprint('review', __name__)


@review.route('/review/overview', methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def overview():

    c_choices = get_country_choices(multinational=True)
    c_choices.insert(0, ('all', 'All'))
    form = ReviewFilter()
    form.country.choices = c_choices

    if request.args:
        overview = get_overview(request.args.get('entity'), 
                                country=request.args.get('country'), 
                                user=request.args.get('user'))

        if request.args.get('country'):
            form.country.data = request.args.get('country')
        if request.args.get('entity'):
            form.entity.data = request.args.get('entity')
    
    else:
        overview = get_overview('all')

    return render_template('review/overview.html', 
                                title='Entries for Review', 
                                show_sidebar=True, 
                                entries=overview,
                                form=form)

@review.route('/review/submit', methods=['POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def submit():
    uid = request.form.get('uid')
    if uid:
        if request.form.get('accept'):
            try:
                accept_entry(uid, current_user)
                flash('Entry has been accepted!', category='success')
                return redirect(url_for('review.overview', **request.args))
            except Exception as e:
                current_app.logger.error(f'Could not accept entry with uid {uid}: {e}')
                flash(f'Reviewing entry failed! Error: {e}', category='danger')
                return redirect(url_for('review.overview', **request.args))
        elif request.form.get('reject'):
            try:
                reject_entry(uid, current_user)
                flash('Entry has been rejected!', category='info')
                return redirect(url_for('review.overview', **request.args))
            except Exception as e:
                current_app.logger.error(f'Could not reject entry with uid {uid}: {e}')
                flash(f'Reviewing entry failed! Error: {e}', category='danger')
                return redirect(url_for('review.overview', **request.args))
        elif request.form.get('edit'):
            try:
                return redirect(url_for('edit.edit_uid', uid=uid))
            except Exception as e:
                current_app.logger.error(f'Could not edit entry with uid {uid}: {e}')
                flash(f'Reviewing entry failed! Error: {e}', category='danger')
                return redirect(url_for('review.overview', **request.args))
        else:
            return abort(404)
    else:
        return abort(404)


@review.route('/review/reject', methods=['POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def reject():
    if request.form.get('uid'):
        try:
            reject_entry(request.form.get('uid'))
            flash('Entry has been rejected!', category='info')
            return redirect(url_for('review.overview'))
        except Exception as e:
            return e
    else:
        return abort(404)

