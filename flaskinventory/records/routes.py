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


@records.route("/new/fieldoptions")
def fieldoptions():
    return jsonify(dgraph.generate_fieldoptions())

@records.route("/new/source")
def new_source():
    return render_template("records/newsource.html")

@records.route('/new/echo', methods=['POST'])
def echo_json():
    return jsonify(request.json)