from flask import (Blueprint, render_template, url_for, flash, redirect, request, abort, jsonify)
from flask_login import login_user, current_user, logout_user, login_required
from flaskinventory.posts.forms import PostForm
from flaskinventory import dgraph
from flaskinventory.records.external import get_geocoords
records = Blueprint('records', __name__)

@records.route("/geocodetest")
def jquerytests():
    return render_template('ajax_geocode_test.html')

@records.route("/external/geocode", methods=['POST'])
def geocode():
    if request.method == 'POST':
        if request.form.get('address'):
            r = get_geocoords(request.form['address'])
            if r:
                return jsonify({'status': 'success', 'content': r})
            else: return jsonify({'status': 'failed'})
        else: return jsonify({'status': 'failed', 'message': 'please supply "address"'})
    
    else: 
        return abort(405)



@records.route("/new/source")
def new_source():
    return render_template("records/newsource.html")



# API Endpoints

@records.route("/new/fieldoptions")
def fieldoptions():
    return jsonify(dgraph.generate_fieldoptions())

@records.route('/new/echo', methods=['POST'])
def echo_json():
    return jsonify(request.json)


@records.route('/_orglookup')
def orglookup():
    query= request.args.get('q')
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