from datetime import datetime
from enum import unique
from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, Markup)
from flask_login import login_user, current_user, logout_user, login_required
from flaskinventory import dgraph
from flaskinventory.review.forms import AcceptButton, RejectButton, ReviewFilter
from flaskinventory.review.dgraph import get_overview, accept_entry, reject_entry, check_entry
from flaskinventory.view.dgraph import get_archive, get_dgraphtype, get_organization, get_source
from flaskinventory.view.utils import make_mini_table

from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.utils import requires_access_level

review = Blueprint('review', __name__)


@review.route('/review/overview', methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def overview():
    countries = dgraph.query(
            '''{ q(func: type("Country")) { name uid } }''')

    c_choices = [(country.get('uid'), country.get('name'))
                    for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])
    c_choices.insert(0, ('all', 'All'))
    form = ReviewFilter()
    form.country.choices = c_choices

    if form.validate_on_submit():
        overview = get_overview(form.entity.data, country=form.country.data)
    else:
        overview = get_overview("Source")

    print(overview)

    return render_template('review/overview.html', 
                                title='Entries for Review', 
                                show_sidebar=True, 
                                entries=overview,
                                form=form)

@review.route('/review/<string:uid>', methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def entry(uid=None):
    if uid:

        accept_button = AcceptButton()
        accept_button.uid.data = uid
        reject_button = RejectButton()
        reject_button.uid.data = uid

        check = check_entry(uid=uid)

        if not check:
            return abort(404)
        
        if check.get('entry_review_status') != 'pending':
            flash(f"Entry is not reviewable! Entry status: {check.get('entry_review_status')}", category='warning')
            return redirect(url_for('review.overview'))

        dgraphtype = check.get('dgraph.type')[0]

        if dgraphtype == 'Source':
            result = get_source(uid=uid)
            if result.get('audience_size'):
                result['audience_size_table'] = make_mini_table(
                result['audience_size'])
            if result.get('audience_residency'):
                result['audience_residency_table'] = make_mini_table(
                    result['audience_residency'])
            related = result.get('related', None)
        
        elif dgraphtype == 'Organization':
            result = get_organization(uid=uid)
        elif dgraphtype == 'Archive':
            result = get_archive(uid=uid)
        elif dgraphtype == 'Dataset':
            result = get_archive(uid=uid)
        else:
            flash(f"Entry is not reviewable! Entry status: {check.get('entry_review_status')}", category='warning')
            return redirect(url_for('review.overview'))

        return render_template('review/detail.html',
                               title=result.get('name'),
                               dgraphtype=dgraphtype,
                               entry=result,
                               show_sidebar=True,
                               related=related,
                               accept_button=accept_button,
                               reject_button=reject_button)

    return abort(404)


@review.route('/review/accept', methods=['POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def accept():
    print(request.form)
    uid = request.form.get('uid')
    if uid:
        try:
            accept_entry(uid)
            flash('Entry has been accepted!', category='success')
            return redirect(url_for('view.view_uid') + f'?uid={uid}')
        except Exception as e:
            return e
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

