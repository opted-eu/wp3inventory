from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory.edit.forms import make_form, RefreshWikidataForm
from flaskinventory.edit.utils import can_edit
from flaskinventory.edit.sanitize import (EditArchiveSanitizer, EditOrgSanitizer, EditSourceSanitizer,
                                          EditSubunitSanitizer, EditDatasetSanitizer, EditMultinationalSanitizer,
                                          WikiDataSanitizer, EditAudienceSizeSanitizer)
from flaskinventory.edit.dgraph import get_entry, get_audience
from flaskinventory.review.dgraph import check_entry
from flaskinventory.misc import get_ip
from flaskinventory.misc.forms import get_country_choices, get_subunit_choices
from flaskinventory.add.external import fetch_wikidata
from flaskinventory.users.constants import USER_ROLES
from flaskinventory import dgraph

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

    if result['q'][0]['dgraph.type'][0] in ['Source', 'Organization', 'Subunit', 'Archive', 'Dataset']:
        return redirect(url_for('edit.' + result['q'][0]['dgraph.type'][0].lower(), unique_name=result['q'][0]['unique_name']))
    else:
        return abort(404)


@edit.route('/edit/organisation/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/organization/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/organisation/uid/<string:uid>', methods=['GET', 'POST'])
@edit.route('/edit/organization/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def organization(unique_name=None, uid=None):
    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Organization':
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')
    if not uid:
        uid = check.get('uid')

    form, fields = make_form('organization')

    form.country.choices = get_country_choices(opted=False)
    if form.validate_on_submit():
        try:
            sanitizer = EditOrgSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('edit.organization', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Organization has been updated', 'success')
            return redirect(url_for('view.view_organization', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('edit.organization', unique_name=form.unique_name.data))

    result = get_entry(unique_name=unique_name)
    if result:
        for key, value in result['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                elif key == 'country':
                    value = value[0].get('uid')
                elif key != 'country':
                    choices = [(subval['uid'], subval['name'])
                               for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                            'choices', choices)

            setattr(getattr(form, key), 'data', value)

        wikidata_form = RefreshWikidataForm()
        wikidata_form.uid.data = uid
        sidebar_items = {'actions': {'wikidata': wikidata_form}, 'meta': result['q'][0]}
        return render_template('edit/editform.html', title='Edit Organization', form=form, fields=fields.keys(), sidebar_items=sidebar_items, show_sidebar=True)
    else:
        return abort(404)


@edit.route('/edit/source/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/source/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def source(unique_name=None, uid=None):

    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Source':
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    result = get_entry(unique_name=unique_name, uid=uid)
    if len(result['q']) == 0:
        return abort(404)

    if result['q'][0].get('audience_size'):
        audience_size_entries = len(result['q'][0]['audience_size'])
    else:
        audience_size_entries = 0

    form, fields = make_form(
        result['q'][0]['channel']['unique_name'], audience_size=audience_size_entries)

    if current_user.user_role >= USER_ROLES.Reviewer:
        form.country.choices = get_country_choices(
            multinational=True, opted=False)
    else:
        form.country.choices = get_country_choices(multinational=True)
    form.geographic_scope_subunit.choices = get_subunit_choices()

    if form.validate_on_submit():
        try:
            sanitizer = EditSourceSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(
                f'Delete Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            # tb_str = ''.join(traceback.format_exception(
            #     None, e, e.__traceback__))
            current_app.logger.error(e)
            flash(
                f'Source could not be updated. Sanitizer raised error: {e}', 'danger')
            return redirect(url_for('edit.source', uid=form.uid.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Source has been updated', 'success')
            return redirect(url_for('view.view_source', unique_name=form.unique_name.data))
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(
                None, e, e.__traceback__))
            current_app.logger.error(e, tb_str)
            flash(
                f'Source could not be updated. DGraph raised error: {e.message}, {e}', 'danger')
            return redirect(url_for('edit.source', uid=form.uid.data))

    for key, value in result['q'][0].items():
        if not hasattr(form, key):
            continue
        if type(value) is dict:
            choices = [(value['uid'], value['name'])]
            value = value['uid']
            setattr(getattr(form, key),
                    'choices', choices)
        elif type(value) is list:
            if type(value[0]) is str:
                value = ",".join(value)
            elif type(value[0]) is int:
                value = [str(val) for val in value]
            else:
                choices = [(subval['uid'], subval['unique_name'])
                           for subval in value if subval.get('unique_name')]
                value = [subval['uid'] for subval in value]
                if key not in ['country', 'geographic_scope_subunit']:
                    setattr(getattr(form, key),
                            'choices', choices)

        setattr(getattr(form, key), 'data', value)

    sidebar_items = {'meta': result['q'][0]}
    if result['q'][0]['channel']['unique_name'] in ['print', 'facebook']:
        sidebar_items['actions'] = {'audience_size': url_for('edit.source_audience', uid=result['q'][0]['uid'])}

    return render_template('edit/editform.html', title='Edit Source', form=form, fields=fields.keys(), show_sidebar=True, sidebar_items=sidebar_items)


@edit.route('/edit/source/uid/<string:uid>/audience', methods=['GET', 'POST'])
@login_required
def source_audience(uid):
    check = check_entry(uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Source':
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
            sanitizer = EditAudienceSizeSanitizer(
            uid, request.get_json(), current_user, get_ip())
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


@edit.route('/edit/subunit/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/subunit/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def subunit(unique_name=None, uid=None):

    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Subunit':
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')

    form, fields = make_form('subunit')

    form.country.choices = get_country_choices(opted=False)
    if form.validate_on_submit():
        try:
            sanitizer = EditSubunitSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Subunit could not be updated: {e}', 'danger')
            return redirect(url_for('edit.subunit', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Subunit has been updated', 'success')
            return redirect(url_for('view.view_subunit', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Subunit could not be updated: {e}', 'danger')
            return redirect(url_for('edit.subunit', unique_name=form.unique_name.data))

    result = get_entry(unique_name=unique_name)
    if result:
        for key, value in result['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                elif key == 'country':
                    value = value[0].get('uid')
                elif key != 'country':
                    choices = [(subval['uid'], subval['name'])
                               for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                            'choices', choices)

            setattr(getattr(form, key), 'data', value)

        sidebar_items = {'meta': result['q'][0]}

        return render_template('edit/editform.html', title='Edit Subunit', form=form, fields=fields.keys(), show_sidebar=True, sidebar_items=sidebar_items)
    else:
        return abort(404)


@edit.route('/edit/multinational/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/multinational/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def multinational(unique_name=None, uid=None):

    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Multinational':
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')

    form, fields = make_form('multinational')

    if form.validate_on_submit():
        try:
            sanitizer = EditMultinationalSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Multinational Entity could not be updated: {e}', 'danger')
            return redirect(url_for('edit.multinational', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Multinational Entity has been updated', 'success')
            return redirect(url_for('view.view_multinational', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Multinational Entity could not be updated: {e}', 'danger')
            return redirect(url_for('edit.multinational', unique_name=form.unique_name.data))

    result = get_entry(unique_name=unique_name)
    if result:
        for key, value in result['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                elif key != 'country':
                    choices = [(subval['uid'], subval['name'])
                               for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                            'choices', choices)

            setattr(getattr(form, key), 'data', value)

        sidebar_items = {'meta': result['q'][0]}

        return render_template('edit/editform.html', title='Edit Multinational Construct', form=form, fields=fields.keys(), show_sidebar=True, sidebar_items=sidebar_items)
    else:
        return abort(404)


@edit.route('/edit/dataset/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/dataset/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def dataset(unique_name=None, uid=None):

    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Dataset':
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')

    form, fields = make_form('dataset')

    if form.validate_on_submit():
        try:
            sanitizer = EditDatasetSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Dataset could not be updated: {e}', 'danger')
            return redirect(url_for('edit.dataset', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Dataset has been updated', 'success')
            return redirect(url_for('view.view_dataset', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Dataset could not be updated: {e}', 'danger')
            return redirect(url_for('edit.dataset', unique_name=form.unique_name.data))

    result = get_entry(unique_name=unique_name)
    if result:
        for key, value in result['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                elif key == 'country':
                    value = value[0].get('uid')
                elif key != 'country':
                    choices = [(subval['uid'], subval['name'])
                               for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                            'choices', choices)

            setattr(getattr(form, key), 'data', value)
        sidebar_items = {'meta': result['q'][0]}
        return render_template('edit/editform.html', title='Edit Dataset', form=form, fields=fields.keys(), show_sidebar=True, sidebar_items=sidebar_items)
    else:
        return abort(404)


@edit.route('/edit/archive/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/archive/uid/<string:uid>', methods=['GET', 'POST'])
@login_required
def archive(unique_name=None, uid=None):

    check = check_entry(unique_name=unique_name, uid=uid)
    if not check:
        return abort(404)

    if check['dgraph.type'][0] != 'Archive':
        if check['dgraph.type'][0] == 'Dataset':
            return dataset(uid=uid)
        return abort(404)

    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name')
    if not uid:
        uid = check.get('uid')

    form, fields = make_form('archive')

    if form.validate_on_submit():
        try:
            sanitizer = EditArchiveSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Archive could not be updated: {e}', 'danger')
            return redirect(url_for('edit.archive', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Archive has been updated', 'success')
            return redirect(url_for('view.view_archive', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Archive could not be updated: {e}', 'danger')
            return redirect(url_for('edit.archive', unique_name=form.unique_name.data))

    result = get_entry(unique_name=unique_name)
    if result:
        for key, value in result['q'][0].items():
            if not hasattr(form, key):
                continue
            if type(value) is list:
                if type(value[0]) is str:
                    value = ",".join(value)
                elif key == 'country':
                    value = value[0].get('uid')
                elif key != 'country':
                    choices = [(subval['uid'], subval['name'])
                               for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                            'choices', choices)

            setattr(getattr(form, key), 'data', value)

        sidebar_items = {'meta': result['q'][0]}

        return render_template('edit/editform.html', title='Edit Archive', form=form, fields=fields.keys(), show_sidebar=True, sidebar_items=sidebar_items)
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

    if check.get('dgraph.type')[0] != "Organization":
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
        sanitizer = WikiDataSanitizer(
            result, current_user, get_ip())
        current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
        current_app.logger.debug(f'Delete Nquads: {sanitizer.delete_nquads}')
    except Exception as e:
        flash(f'Entry could not be updated: {e}', 'danger')
        return redirect(url_for('edit.edit_uid', uid=uid))

    try:
        delete = dgraph.upsert(
            sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
        current_app.logger.debug(delete)
        result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
        current_app.logger.debug(result)
        flash(f'WikiData has been refreshed', 'success')
        return redirect(url_for('edit.edit_uid', uid=uid))
    except Exception as e:
        flash(f'Could not refresh WikiData: {e}', 'danger')
        return redirect(url_for('edit.edit_uid', uid=uid))
