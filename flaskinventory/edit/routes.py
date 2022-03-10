from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.flaskdgraph import Schema
from flaskinventory.main.sanitizer import Sanitizer
from flaskinventory.misc import get_ip
from flaskinventory.add.external import fetch_wikidata

from flaskinventory.edit.forms import RefreshWikidataForm
from flaskinventory.edit.utils import can_edit, channel_filter
from flaskinventory.edit.sanitizer import EditAudienceSizeSanitizer
from flaskinventory.edit.dgraph import get_entry, get_audience
from flaskinventory.review.dgraph import check_entry

import traceback

edit = Blueprint('edit', __name__)


@edit.route('/edit/uid/<string:uid>')
@login_required
def edit_uid(uid):
    query_string = f'''{{ q(func: uid({uid})) {{
		uid unique_name entry_review_status dgraph.type }} }}'''

    result = dgraph.query(query_string)

    if len(result['q']) == 0:
        return abort(404)

    if not result['q'][0].get('dgraph.type'):
        return abort(404)

    if 'Entry' in result['q'][0]['dgraph.type']:
        result['q'][0]['dgraph.type'].remove('Entry')
    if 'Resource' in result['q'][0]['dgraph.type']:
        result['q'][0]['dgraph.type'].remove('Resource')

    if result['q'][0]['dgraph.type'][0] in Schema.get_types():
        return redirect(url_for('edit.entry', dgraph_type=result['q'][0]['dgraph.type'][0].title(), unique_name=result['q'][0]['unique_name'], **request.args))
    else:
        return abort(404)


@edit.route('/edit/wikidata', methods=['POST'])
@login_required
def refresh_wikidata():

    uid = request.form.get('uid')
    if not uid:
        flash('Need to specify a UID', 'danger')
        return redirect(url_for('users.my_entries'))

    check = check_entry(uid=uid)
    if not check:
        flash('UID not found!', 'danger')
        return redirect(url_for('users.my_entries'))

    if "Organization" not in check.get('dgraph.type'):
        flash('Only works with organizations!', 'danger')
        return redirect(url_for('view.view_uid', uid=uid))

    if not can_edit(check, current_user):
        flash('You do not have permissions to edit this entry', 'danger')
        return redirect(url_for('view.view_uid', uid=uid))

    query_string = f'''{{ q(func: uid({uid})) {{wikidataID}} }}'''

    entry = dgraph.query(query_string)
    try:
        wikidataid = entry['q'][0]['wikidataID']
    except:
        flash(f"Entry {uid} does not have a wikidata ID", 'danger')
        return redirect(url_for('view.view_uid', uid=uid))

    result = fetch_wikidata(f"Q{wikidataid}")

    if result:
        result['uid'] = uid
    else:
        flash(f"Could not retrieve wikidata", 'danger')
        return redirect(url_for('view.view_uid', uid=uid))

    try:
        sanitizer = Sanitizer.edit(result, dgraph_type="Organization")
        current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
        current_app.logger.debug(f'Delete Nquads: {sanitizer.delete_nquads}')
    except Exception as e:
        flash(f'Entry could not be updated: {e}', 'danger')
        return redirect(url_for('edit.edit_uid', uid=uid))

    try:
        result = dgraph.upsert(
            sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads, set_nquads=sanitizer.set_nquads)
        current_app.logger.debug(result)
        flash(f'WikiData has been refreshed', 'success')
        return redirect(url_for('edit.edit_uid', uid=uid))
    except Exception as e:
        flash(f'Could not refresh WikiData: {e}', 'danger')
        return redirect(url_for('edit.edit_uid', uid=uid))


@edit.route('/edit/<string:dgraph_type>/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/<string:dgraph_type>/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def entry(dgraph_type=None, unique_name=None, uid=None):
    if not dgraph_type:
        return abort(404)
    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)
    
    dgraph_type = dgraph_type.title()
    if dgraph_type not in check['dgraph.type']:
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if current_user.user_role < Schema.permissions_edit(dgraph_type):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')
    if not uid:
        uid = check.get('uid')

    try:
        entry = get_entry(uid=uid)
    except Exception as e:
        current_app.logger.error(f'Could not populate form for <{uid}>: {e}', stack_info=True)
        return abort(404)

    skip_fields = []
    # manually filter out fields depending on channel
    if dgraph_type == 'Source':
        skip_fields = channel_filter(entry['q'][0]['channel']['unique_name'])

    if request.method == 'GET':
        form = Schema.generate_edit_entry_form(dgraph_type=dgraph_type, populate_obj=entry['q'][0], entry_review_status=check['entry_review_status'], skip_fields=skip_fields)
    else:
        form = Schema.generate_edit_entry_form(dgraph_type=dgraph_type, entry_review_status=check['entry_review_status'], skip_fields=skip_fields)
    
    fields = Schema.get_predicates(dgraph_type)

    if form.validate_on_submit():
        try:
            sanitizer = Sanitizer.edit(form.data, dgraph_type=dgraph_type)
        except Exception as e:
            if current_app.debug:
                    e_trace = "".join(traceback.format_exception(
                        None, e, e.__traceback__))
                    current_app.logger.error(e_trace)
            flash(f'{dgraph_type} could not be updated: {e}', 'danger')
            return redirect(url_for('edit.entry', dgraph_type=dgraph_type, uid=uid))
        try:
            result = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads, set_nquads=sanitizer.set_nquads)
            if request.form.get('accept'):
                flash(f'{dgraph_type} has been edited and accepted', 'success')
                return redirect(url_for('review.overview', **request.args))
            else:
                flash(f'{dgraph_type} has been updated', 'success')
                return redirect(url_for('view.view_uid', uid=uid))
        except Exception as e:
            flash(f'{dgraph_type} could not be updated: {e}', 'danger')
            return redirect(url_for('edit.entry', dgraph_type=dgraph_type, uid=uid))

    sidebar_items = {'meta': entry['q'][0]}
    if dgraph_type == 'Organization':
        wikidata_form = RefreshWikidataForm()
        wikidata_form.uid.data = uid
        sidebar_items.update({'actions': {'wikidata': wikidata_form}})
    if dgraph_type == 'Source':
        if entry['q'][0]['channel']['unique_name'] in ['print', 'facebook']:
            sidebar_items['actions'] = {'audience_size': url_for('edit.source_audience', uid=entry['q'][0]['uid'])}

    return render_template('edit/editform.html', title=f'Edit {dgraph_type}', form=form, fields=fields.keys(), sidebar_items=sidebar_items, show_sidebar=True)

@edit.route('/edit/source/uid/<string:uid>/audience', methods=['GET', 'POST'])
@login_required
def source_audience(uid):
    check = check_entry(uid=uid)
    if not check:
        return abort(404)

    if 'Source' not in check['dgraph.type']:
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if check['channel']['unique_name'] not in ['print', 'facebook']:
        flash('You can only edit the audience size for print and Facebook news sources', 'info')
        return redirect(url_for('edit.source', uid=uid))

    if request.method == 'POST':
        current_app.logger.debug(
            f'received POST request: {request.get_json()}')
        try:
            sanitizer = EditAudienceSizeSanitizer(uid, request.get_json())
        except Exception as e:
            return jsonify({'status': 'error', 'error': f'{e}'})
        
        try:
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Delete Nquads: {sanitizer.delete_nquads}')

            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
        except Exception as e:
            return jsonify({'status': 'error', 'error': f'{e}'})

        flash('Audience size updated!', 'success')

        return jsonify({'status': 'success', 'redirect': url_for('view.view_source', uid=uid)})

    audience_size = get_audience(uid=uid)
    entry = get_entry(uid=uid)
    entry = entry['q'][0]
    sidebar_items = {'meta': entry}

    return render_template('edit/audience.html', title='Edit Source', entry=entry, data=audience_size, show_sidebar=True, sidebar_items=sidebar_items)

