import asyncio
import json
from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.add.forms import NewEntry
from flaskinventory.add.utils import database_check_table
from flaskinventory.add.process import EntryProcessor
from flaskinventory.add.dgraph import generate_fieldoptions

import traceback

add = Blueprint('add', __name__)


@add.route("/add", methods=['GET', 'POST'])
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
            return render_template('add/database_check.html', query=form.name.data, table=table)
            # return redirect(url_for('add.database_check', result=result['data']))
        else:
            return redirect(url_for('add.new_source', entry_name=form.name.data))
    return render_template('add/newentry.html', form=form)


@add.route("/add/source")
@login_required
def new_source():
    draft = None
    if request.args.get('draft'):
        query_string = f"""{{ q(func: uid({request.args.get('draft')})) {{ uid
                                expand(_all_) {{ uid unique_name name dgraph.type channel {{ name }}
                                            }}
                                publishes_org: ~publishes @filter(eq(is_person, false)) {{
                                    uid unique_name name ownership_kind country {{ name }} }}
                                publishes_person: ~publishes @filter(eq(is_person, true)) {{
                                    uid unique_name name ownership_kind country {{ name }} }}
                                archives: ~sources_included @facets @filter(type("Archive")) {{ 
                                    uid unique_name name }} 
                                datasets: ~sources_included @facets @filter(type("Dataset")) {{ 
                                    uid unique_name name }} 
                                }} }}"""
        draft = dgraph.query(query_string)
    if draft:
        print(draft)
        draft = json.dumps(draft['q'][0], default=str)
    return render_template("add/newsource.html", draft=draft)


@add.route("/add/confirmation")
def confirmation():
    return render_template("not_implemented.html")


@add.route("/add/draft/<string:entity>/<string:uid>")
def from_draft(entity, uid):
    return jsonify({"entity": entity, "uid": uid})

# API Endpoints

# cache this route
@add.route("/add/fieldoptions")
async def fieldoptions():
    data = await generate_fieldoptions()
    return jsonify(data)


@add.route('/new/submit', methods=['POST'])
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
            'view.view_source', uid=result['newsource'])
        return jsonify(result)
    else:
        return jsonify({'error': 'DGraph Error - Could not perform mutation'})


@add.route('/new/echo', methods=['POST'])
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


@add.route('/_orglookup')
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


@add.route('/_sourcelookup')
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

