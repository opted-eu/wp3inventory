"""
Endpoints contains all routes that do not return rendered templates,
but some form of json or data.
Routes here are to interface with JavaScript components
Also for a potential API
"""

import traceback
from flask import (current_app, Blueprint, request, jsonify, url_for)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.flaskdgraph.utils import strip_query
from flaskinventory.add.sanitize import SourceSanitizer
from flaskinventory.misc import get_ip
from flaskinventory.add.dgraph import generate_fieldoptions


endpoint = Blueprint('endpoint', __name__)


@endpoint.route('/endpoint/quicksearch')
def quicksearch():
    query = request.args.get('q')
    # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
    query_string = f'''
            query quicksearch($name: string)
            {{
            field1 as var(func: anyofterms(name, $name))
            field2 as var(func: anyofterms(other_names, $name))
            field3 as var(func: anyofterms(title, $name))
            
            data(func: uid(field1, field2, field3)) 
                @normalize @filter(eq(entry_review_status, "accepted")) {{
                    uid 
                    unique_name: unique_name 
                    name: name 
                    other_names: other_names
                    type: dgraph.type 
                    title: title
                    channel {{ channel: name }}
                }}
            }}
        '''
    result = dgraph.query(query_string, variables={'$name': query})
    result['status'] = True
    return jsonify(result)

@endpoint.route('/endpoint/orglookup')
def orglookup():
    query = strip_query(request.args.get('q'))
    person = request.args.get('person')
    if person:
        person_filter = f'AND eq(is_person, {person})'
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


@endpoint.route('/endpoint/sourcelookup')
def sourcelookup():
    query = strip_query(request.args.get('q'))
    query_string = f'''{{
            field1 as var(func: regexp(name, /{query}/i)) @filter(type("Source"))
            field2 as var(func: regexp(other_names, /{query}/i)) @filter(type("Source"))
  
	        data(func: uid(field1, field2)) {{
                uid
                unique_name
                name
                channel {{ name }}
                country {{ name }}
                }}
            }}
    '''
    try:
        result = dgraph.query(query_string)
        result['status'] = True
        return jsonify(result)
    except Exception as e:
        current_app.logger.warning(f'could not lookup source with query "{query}". {e}')
        return jsonify({'status': False, 'error': f'e'})

# cache this route
@endpoint.route("/endpoint/new/fieldoptions")
async def fieldoptions():
    data = await generate_fieldoptions()
    return jsonify(data)

@endpoint.route('/endpoint/new/submit', methods=['POST'])
def submit():
    try:
        sanitizer = SourceSanitizer(
            request.json, current_user, get_ip())
        current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
        current_app.logger.debug(f'Delete Nquads: {sanitizer.delete_nquads}')
    except Exception as e:
        error = {'error': f'{e}'}
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        current_app.logger.error(tb_str)
        return jsonify(error)

    if sanitizer.is_upsert:
        try:
            result = dgraph.upsert(
                sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
        except Exception as e:
            error = {'error': f'{e}'}
            tb_str = ''.join(traceback.format_exception(
                None, e, e.__traceback__))
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

