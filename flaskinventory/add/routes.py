import asyncio
import json
from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.add.forms import NewEntry
from flaskinventory.add.utils import database_check_table
from flaskinventory.add.process import EntryProcessor
from flaskinventory.add.sanitize import SourceSanitizer
from flaskinventory.add.dgraph import generate_fieldoptions
from flaskinventory.users.constants import USER_ROLES

import traceback

add = Blueprint('add', __name__)


@add.route("/add", methods=['GET', 'POST'])
@login_required
def new_entry():
    form = NewEntry()
    if form.validate_on_submit():
        query_string = f'''{{
                field1 as var(func: regexp(name, /{form.name.data}/i)) @filter(type("{form.entity.data}"))
                field2 as var(func: anyofterms(name, "{form.name.data}")) @filter(type("{form.entity.data}"))
                field3 as var(func: anyofterms(other_names, "{form.name.data}")) @filter(type("{form.entity.data}"))
    
                data(func: uid(field1, field2, field3)) {{
                    uid
                    unique_name
                    name
                    other_names
                    channel {{ name }}
                    geographic_scope_countries {{ name }}
                    entry_review_status
                    }}
                }}
        '''
        result = dgraph.query(query_string)
        if len(result['data']) > 0:
            return render_template('add/database_check.html', query=form.name.data, result=result['data'])
            # return redirect(url_for('add.database_check', result=result['data']))
        else:
            return redirect(url_for('add.new_source', entry_name=form.name.data))
    return render_template('add/newentry.html', form=form)


@add.route("/add/source")
@login_required
def new_source(draft=None):
    if draft is None:
        draft = request.args.get('draft')
    if draft:
        query_string = f"""{{ q(func: uid({draft}))  @filter(eq(entry_review_status, "draft")) {{ uid
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
        if len(draft['q']) > 0:
            draft = draft['q'][0]
            entry_added = draft.pop('entry_added')
            draft = json.dumps(draft, default=str)
            # check permissions
            if current_user.uid != entry_added['uid']:
                if current_user.user_role >= USER_ROLES.Reviewer:
                    flash("You are editing another user's draft", category='info')
                else:
                    draft = None
                    flash('You can only edit your own drafts!', category='warning')
        else:
            draft = None
    return render_template("add/newsource.html", draft=draft)


@add.route("/add/confirmation")
def confirmation():
    return render_template("not_implemented.html")

@login_required
@add.route("/add/draft/<string:entity>/<string:uid>")
@add.route("/add/draft/")
def from_draft(entity=None, uid=None):
    if entity and uid:
        if entity == 'Source':
            return new_source(draft=uid)
        else:
            return render_template("not_implemented.html")
    
    query_string = f"""{{ q(func: uid({current_user.uid})) {{
                user_displayname
                uid
                drafts: ~entry_added @filter(type(Source) and eq(entry_review_status, "draft")) 
                @facets(orderdesc: timestamp) (first: 1) {{ uid }}
            }} }}"""
        
    result = dgraph.query(query_string)
    if result['q'][0].get('drafts'):
        return new_source(draft=result['q'][0]['drafts'][0]['uid'])
    else:
        return redirect(url_for('users.my_entries'))

# API Endpoints

# cache this route
@add.route("/add/fieldoptions")
async def fieldoptions():
    data = await generate_fieldoptions()
    return jsonify(data)


@add.route('/new/submit', methods=['POST'])
def submit():
    try:
        sanitizer = SourceSanitizer(
            request.json, current_user, request.remote_addr)
        current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
        current_app.logger.debug(f'Set Nquads: {sanitizer.delete_nquads}')
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)

    if sanitizer.is_upsert:
        try:
            result = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
        except Exception as e:
            error = {'error': f'{e}'}
            tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            current_app.logger.error(tb_str)
            return jsonify(error)

    try:
        result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)

    if result:
        if sanitizer.is_upsert:
            uid = str(sanitizer.uid)
        else:
            newuids = dict(result.uids)
            uid = newuids['newsource']
        response = {'redirect': url_for(
            'view.view_source', uid=uid)}

        return jsonify(response)
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
    if person:
        person_filter =  f'AND eq(is_person, {person})'
    else:
        person_filter = ''
    # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
    query_string = f'''{{
            field1 as var(func: regexp(name, /{query}/i)) @filter(type("Organization") {person_filter})
            field2 as var(func: regexp(other_names, /{query}/i)) @filter(type("Organization") {person_filter})
  
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

