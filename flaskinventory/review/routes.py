from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort)
from flask_login import login_required
from flaskinventory import dgraph
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.review.forms import ReviewActions, ReviewFilter
from flaskinventory.review.dgraph import get_overview, accept_entry, reject_entry, check_entry
from flaskinventory.view.dgraph import get_archive, get_dgraphtype, get_organization, get_source, get_subunit
from flaskinventory.view.utils import make_mini_table

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

@review.route('/review/<string:uid>', methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def entry(uid=None):
    if uid:

        review_actions = ReviewActions()
        review_actions.uid.data = uid

        check = check_entry(uid=uid)

        if not check:
            return abort(404)
        
        if check.get('entry_review_status') != 'pending':
            flash(f"Entry is not reviewable! Entry status: {check.get('entry_review_status')}", category='warning')
            return redirect(url_for('review.overview'))

        dgraphtype = check.get('dgraph.type')[0]
        show_sidebar = False
        related = None
        if dgraphtype == 'Source':
            show_sidebar = True
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
        elif dgraphtype == 'Subunit':
            result = get_subunit(uid=uid)
        else:
            flash(f"Entry is not reviewable! Entry status: {check.get('entry_review_status')}", category='warning')
            return redirect(url_for('review.overview'))

        return render_template('review/detail.html',
                               title=f"Review: {result.get('name')}",
                               dgraphtype=dgraphtype,
                               entry=result,
                               show_sidebar=show_sidebar,
                               related=related,
                               review_actions=review_actions)

    return abort(404)


@review.route('/review/submit', methods=['POST'])
@login_required
@requires_access_level(USER_ROLES.Reviewer)
def submit():
    uid = request.form.get('uid')
    if uid:
        if request.form.get('accept'):
            try:
                accept_entry(uid)
                flash('Entry has been accepted!', category='success')
                return redirect(url_for('review.overview', **request.args))
            except Exception as e:
                return e
        elif request.form.get('reject'):
            try:
                reject_entry(uid)
                flash('Entry has been rejected!', category='info')
                return redirect(url_for('review.overview', **request.args))
            except Exception as e:
                return e
        elif request.form.get('edit'):
            try:
                return redirect(url_for('edit.edit_uid', uid=uid))
            except Exception as e:
                return e
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

