from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort)
from flask_login import current_user, login_required
from flaskinventory.edit.forms import make_form
from flaskinventory.edit.sanitize import EditOrgSanitizer, EditSourceSanitizer

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

    if result['q'][0]['dgraph.type'][0] in ['Source', 'Organization']:
        return redirect(url_for('edit.' + result['q'][0]['dgraph.type'][0].lower(), unique_name=result['q'][0]['unique_name']) )



@edit.route('/edit/organisation/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/organization/<string:unique_name>', methods=['GET', 'POST'])
@login_required
def organization(unique_name):
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

    form, fields = make_form(result['q'][0]['channel']['unique_name'], audience_size=len(result['q'][0]['audience_size']))
    countries = dgraph.query('''{ countries(func: type("Country")) { name uid } subunits(func: type("Subunit")) { name uid }}''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['countries']]
    c_choices = sorted(c_choices, key=lambda x: x[1])
    form.geographic_scope_countries.choices = c_choices

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
                if key not in ['geographic_scope_countries', 'geographic_scope_subunit']:
                    setattr(getattr(form, key),
                            'choices', choices)
               
        setattr(getattr(form, key), 'data', value)

    return render_template('edit/editform.html', title='Edit Source', form=form, fields=fields.keys())

# @edit.route('/edit/source/<string:uid>', methods=['GET', 'POST'])
# @login_required
# def edit_source(uid):

#     form = make_form(editprintfields)
#     countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
#     c_choices = [(country.get('uid'), country.get('name'))
#                  for country in countries['q']]
#     c_choices = sorted(c_choices, key=lambda x: x[1])

#     form.geographic_scope_countries.choices = c_choices
#     if form.validate_on_submit():
#         try:
#             sanitize_edit_org(form.data)
#             flash(f'Source has been updated', 'success')
#             return redirect(url_for('view.view_source', unique_name=form.unique_name.data))
#         except Exception as e:
#             flash(f'Organization could not be updated: {e}', 'danger')
#             return redirect(url_for('add.organization', unique_name=form.unique_name.data))

#     query_string = f'''{{ q(func: uid({uid})) {{
# 		uid expand(_all_) 
#          }} }}'''

#     result = dgraph.query(query_string)
#     if result:
#         for key, value in result['q'][0].items():
#             if '|' in key:
#                 continue
#             if type(value) is list:
#                 if type(value[0]) is str:
#                     value = ", ".join(value)
#                 elif type(value[0]) is datetime:
#                     continue
#                 elif key != 'geographic_scope_countries':
#                     value_unique_name = ", ".join(
#                         [subval['unique_name'] for subval in value])
#                     value = ", ".join([subval['uid'] for subval in value])
#                     setattr(getattr(form, key + '_unique_name'),
#                             'data', value_unique_name)
#             if hasattr(form, key):
#                 setattr(getattr(form, key), 'data', value)
#             else:
#                 setattr(form, key, StringField(key))
#                 setattr(getattr(form, key), 'data', value)

#         return render_template('edit/source.html', title='Edit Source', form=form, fields=editprintfields)
#     else:
#         return abort(404)
