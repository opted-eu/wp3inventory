from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.records.forms import NewEntry, OrganizationForm
from flaskinventory.records.utils import database_check_table, sanitize_edit_org
from flaskinventory.records.process import EntryProcessor
from flaskinventory.records.dgraph import generate_fieldoptions

import traceback

records = Blueprint('records', __name__)


@records.route("/new", methods=['GET', 'POST'])
@login_required
def new_entry():
    form = NewEntry()
    if form.validate_on_submit():
        query_string = f'''{{
                field1 as var(func: match(name, "{form.name.data}", 8)) @filter(type("{form.entity.data}"))
                field2 as var(func: match(other_names, "{form.name.data}", 8)) @filter(type("{form.entity.data}"))
    
                data(func: uid(field1, field2)) @normalize {{
                    uid
                    unique_name: unique_name
                    name: name
                    other_names: other_names
                    channel {{ channel: name }}
                    geographic_scope_countries {{ country: name }}
                    }}
                }}
        '''
        result = dgraph.query(query_string)
        if len(result['data']) > 0:
            for item in result['data']:
                if item.get('other_names'):
                    item['other_names'] = ", ".join(item['other_names'])
            table = database_check_table(result['data'])
            return render_template('records/database_check.html', query=form.name.data, table=table)
            # return redirect(url_for('records.database_check', result=result['data']))
        else:
            return redirect(url_for('records.new_source', entry_name=form.name.data))
    return render_template('records/newentry.html', form=form)


@records.route("/new/source")
@login_required
def new_source():
    return render_template("records/newsource.html")


@records.route("/new/confirmation")
def confirmation():
    return render_template("not_implemented.html")

# API Endpoints


@records.route("/new/fieldoptions")
def fieldoptions():
    return jsonify(generate_fieldoptions())


@records.route('/new/submit', methods=['POST'])
def submit():
    try:
        processor = EntryProcessor(
            request.json, current_user, request.remote_addr)
        current_app.logger.debug(f'Mutation Object: {processor.mutation}')
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)

    try:
        result = dgraph.mutation(processor.mutation)
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)

    if result:
        result = dict(result.uids)
        result['redirect'] = url_for(
            'inventory.view_source', uid=result['newsource'])
        return jsonify(result)
    else:
        return jsonify({'error': 'DGraph Error - Could not perform mutation'})


@records.route('/new/echo', methods=['POST'])
def echo_json():
    try:
        processor = EntryProcessor(
            request.json, current_user, request.remote_addr)
        current_app.logger.debug(f'Mutation Object: {processor.mutation}')
        return jsonify(processor.mutation)
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)


@records.route('/_orglookup')
def orglookup():
    query = request.args.get('q')
    person = request.args.get('person')
    # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
    query_string = f'''{{
            field1 as var(func: regexp(name, /{query}/i)) @filter(type("Organization") AND eq(is_person, {person}))
            field2 as var(func: regexp(other_names, /{query}/i)) @filter(type("Organization") AND eq(is_person, {person}))
  
	        data(func: uid(field1, field2)) {{
                uid
                unique_name
                name
                dgraph.type
                is_person
                other_names
                country {{ name }}
                }}
            }}
    '''
    result = dgraph.query(query_string)
    result['status'] = True
    return jsonify(result)


@records.route('/_sourcelookup')
def sourcelookup():
    query = request.args.get('q')
    query_string = f'''{{
            field1 as var(func: regexp(name, /{query}/i)) @filter(type("Source"))
            field2 as var(func: regexp(other_names, /{query}/i)) @filter(type("Source"))
  
	        data(func: uid(field1, field2)) {{
                uid
                unique_name
                name
                channel {{ name }}
                geographic_scope_countries {{ name }}
                }}
            }}
    '''
    result = dgraph.query(query_string)
    result['status'] = True
    return jsonify(result)


@records.route('/edit/organisation/<string:unique_name>', methods=['GET', 'POST'])
@records.route('/edit/organization/<string:unique_name>', methods=['GET', 'POST'])
@login_required
def edit_organization(unique_name):
    form = OrganizationForm()
    countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])

    form.country.choices = c_choices
    if form.validate_on_submit():
        try:
            sanitize_edit_org(form.data)
            flash(f'Organization has been updated', 'success')
            return redirect(url_for('inventory.view_organization', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('records.edit_organization', unique_name=form.unique_name.data))

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
    if result:
        for key, value in result['q'][0].items():
            if type(value) is list:
                if type(value[0]) is str:
                    value = ", ".join(value)
                elif key != 'country':
                    value_unique_name = ", ".join(
                        [subval['unique_name'] for subval in value])
                    value = ", ".join([subval['uid'] for subval in value])
                    setattr(getattr(form, key + '_unique_name'),
                            'data', value_unique_name)
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/organization.html', title='Edit Organization', form=form)
    else:
        return abort(404)
