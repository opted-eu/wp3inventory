from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort)
from flask_login import current_user, login_required
from flaskinventory.edit.forms import make_form
from flaskinventory.edit.utils import can_edit
from flaskinventory.edit.sanitize import EditArchiveSanitizer, EditOrgSanitizer, EditSourceSanitizer, EditSubunitSanitizer, EditDatasetSanitizer
from flaskinventory.review.dgraph import check_entry
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
        return redirect(url_for('edit.' + result['q'][0]['dgraph.type'][0].lower(), unique_name=result['q'][0]['unique_name']) )
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

    form, fields = make_form('organization')
    countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])

    form.country.choices = c_choices
    if form.validate_on_submit():
        try:
            sanitizer = EditOrgSanitizer(
                form.data, current_user, request.remote_addr)
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('edit.organization', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Organization has been updated', 'success')
            return redirect(url_for('view.view_organization', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('edit.organization', unique_name=form.unique_name.data))
      

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ name unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
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
                    choices = [(subval['uid'], subval['name']) for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                                'choices', choices)
                    
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/editform.html', title='Edit Organization', form=form, fields=fields.keys())
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

    if unique_name:
        query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
                            uid expand(_all_) {{ name unique_name uid }}
                            }} }}'''
    elif uid:
        query_string = f'''{{ q(func: uid({uid})) {{
                                uid expand(_all_) {{ name unique_name uid }}
                                }} }}'''

    result = dgraph.query(query_string)
    if len(result['q']) == 0:
        return abort(404)
    
    if result['q'][0].get('audience_size'):
        audience_size_entries = len(result['q'][0]['audience_size'])
    else:
        audience_size_entries = 0

    form, fields = make_form(result['q'][0]['channel']['unique_name'], audience_size=audience_size_entries)
    countries = dgraph.query('''{ countries(func: type("Country")) { name uid } subunits(func: type("Subunit")) { name uid }}''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['countries']]
    c_choices = sorted(c_choices, key=lambda x: x[1])
    form.country.choices = c_choices

    su_choices = [(subunit.get('uid'), subunit.get('name'))
                 for subunit in countries['subunits']]
    su_choices = sorted(su_choices, key=lambda x: x[1])
    form.geographic_scope_subunit.choices = su_choices

    if form.validate_on_submit():
        try:
            sanitizer = EditSourceSanitizer(
                form.data, current_user, request.remote_addr)
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            current_app.logger.error(e, tb_str)
            flash(f'Source could not be updated. Sanitizer raised error: {e}', 'danger')
            return redirect(url_for('edit.source', uid=form.uid.data))

        try:
            delete = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Source has been updated', 'success')
            return redirect(url_for('view.view_source', unique_name=form.unique_name.data))
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            current_app.logger.error(e, tb_str)
            flash(f'Source could not be updated. DGraph raised error: {e.message}, {e}', 'danger')
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
                choices = [(subval['uid'], subval['unique_name']) for subval in value]
                value = [subval['uid'] for subval in value]
                if key not in ['country', 'geographic_scope_subunit']:
                    setattr(getattr(form, key),
                            'choices', choices)
               
        setattr(getattr(form, key), 'data', value)

    return render_template('edit/editform.html', title='Edit Source', form=form, fields=fields.keys())



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
    countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])

    form.country.choices = c_choices
    if form.validate_on_submit():
        try:
            sanitizer = EditSubunitSanitizer(
                form.data, current_user, request.remote_addr)
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Subunit could not be updated: {e}', 'danger')
            return redirect(url_for('edit.subunit', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Subunit has been updated', 'success')
            return redirect(url_for('view.view_subunit', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Subunit could not be updated: {e}', 'danger')
            return redirect(url_for('edit.subunit', unique_name=form.unique_name.data))
      

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ name unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
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
                    choices = [(subval['uid'], subval['name']) for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                                'choices', choices)
                    
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/editform.html', title='Edit Subunit', form=form, fields=fields.keys())
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
                form.data, current_user, request.remote_addr)
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Dataset could not be updated: {e}', 'danger')
            return redirect(url_for('edit.dataset', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Dataset has been updated', 'success')
            return redirect(url_for('view.view_subunit', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Dataset could not be updated: {e}', 'danger')
            return redirect(url_for('edit.dataset', unique_name=form.unique_name.data))
      

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ name unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
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
                    choices = [(subval['uid'], subval['name']) for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                                'choices', choices)
                    
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/editform.html', title='Edit Dataset', form=form, fields=fields.keys())
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
        return abort(404)
    
    if not can_edit(check, current_user):
        return abort(403)

    if not unique_name:
        unique_name = check.get('unique_name') 


    form, fields = make_form('archive')
    
    if form.validate_on_submit():
        try:
            sanitizer = EditArchiveSanitizer(
                form.data, current_user, request.remote_addr)
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
        except Exception as e:
            flash(f'Archive could not be updated: {e}', 'danger')
            return redirect(url_for('edit.archive', unique_name=form.unique_name.data))

        try:
            delete = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
            current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Archive has been updated', 'success')
            return redirect(url_for('view.view_subunit', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Archive could not be updated: {e}', 'danger')
            return redirect(url_for('edit.archive', unique_name=form.unique_name.data))
      

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ name unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
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
                    choices = [(subval['uid'], subval['name']) for subval in value]
                    value = [subval['uid'] for subval in value]
                    setattr(getattr(form, key),
                                'choices', choices)
                    
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/editform.html', title='Edit Archive', form=form, fields=fields.keys())
    else:
        return abort(404)