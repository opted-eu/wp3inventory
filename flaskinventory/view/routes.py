from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.flaskdgraph.dgraph_types import SingleChoice
from flaskinventory.flaskdgraph import Schema, build_query_string
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.utils import requires_access_level
from flaskinventory.view.dgraph import (get_entry, get_rejected, list_by_type)
from flaskinventory.view.utils import can_view
from flaskinventory.view.forms import SimpleQuery
from flaskinventory.flaskdgraph.utils import validate_uid, restore_sequence
from flaskinventory.review.utils import create_review_actions

view = Blueprint('view', __name__)

@view.route('/search')
def search():
    if request.args.get('query'):
        query = request.args.get('query')
        if validate_uid(query):
            return view_uid(uid=validate_uid(query))
        # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
        query_string = f'''
                query search($name: string)
                {{
                field1 as a(func: anyofterms(name, $name))
                field2 as b(func: anyofterms(other_names, $name))
                field3 as c(func: anyofterms(title, $name))
                field4 as d(func: eq(doi, $name))
                field5 as e(func: eq(arxiv, $name))
                field6 as f(func: anyofterms(authors, $name))
                
                data(func: uid(field1, field2, field3, field4, field5, field6)) 
                    @normalize @filter(eq(entry_review_status, "accepted")) {{
                        uid 
                        unique_name: unique_name 
                        name: name 
                        other_names: other_names
                        type: dgraph.type 
                        title: title
                        channel {{ channel: name }}
                        country {{ country: name }}
                        doi: doi
                        arxiv: arxiv
                        authors: authors @facets
                        published_date: published_date
                    }}
                }}
        '''
        result = dgraph.query(query_string, variables={'$name': query})

        if len(result['data']) > 0:
            result = result['data']
            for item in result:
                if 'Entry' in item['type']:
                    item['type'].remove('Entry')
                if any(t in item['type'] for t in ['ResearchPaper', 'Tool', 'Corpus', 'Dataset']):
                    restore_sequence(item)
        else:
            result = None

        

        # CACHE THIS
        c_choices = get_country_choices()
        c_choices.insert(0, ('all', 'All'))
        form = SimpleQuery()
        form.country.choices = c_choices
        return render_template('search_result.html', title='Query Result', result=result, show_sidebar=True, sidebar_title="Query", sidebar_form=form)
    else:
        flash("Please enter a search query in the top search bar", "info")
        return redirect(url_for('main.home'))

@view.route("/view")
@view.route("/view/uid/<string:uid>")
def view_uid(uid=None):
    request_args = request.args.to_dict()
    if request_args.get('uid'):
        uid = request_args.pop('uid')
    
    uid = validate_uid(uid)
    if not uid:
        return abort(404)
    dgraphtype = dgraph.get_dgraphtype(uid)
    if dgraphtype:
        if dgraphtype.lower() == 'rejected':
            return redirect(url_for('view.view_rejected', uid=uid))
        return redirect(url_for('view.view_generic', dgraph_type=dgraphtype, uid=uid, **request_args))
    else:
        return abort(404)


@login_required
@view.route("/view/rejected/<uid>")
def view_rejected(uid):
    uid = validate_uid(uid)
    if not uid:
        flash('Invalid ID provided!', "warning")
        return abort(404)

    data = get_rejected(uid)

    if not data:
        return abort(404)
    
    if not can_view(data, current_user):
        return abort(403)
    
    return render_template('view/rejected.html',
                               title=f"Rejected: {data.get('name')}",
                               entry=data)


@view.route("/view/<string:dgraph_type>/uid/<uid>")
@view.route("/view/<string:dgraph_type>/<string:unique_name>")
def view_generic(dgraph_type=None, uid=None, unique_name=None):
    dgraph_type = Schema.get_type(dgraph_type)
    if not dgraph_type:
        if uid:
            return redirect(url_for('view.view_uid', uid=uid))
        else:
            return abort(404)

    data = get_entry(uid=uid, unique_name=unique_name, dgraph_type=dgraph_type)

    if not data:
        return abort(404)

    if any(x in data['dgraph.type'] for x in ['Source', 'Organization']):
        show_sidebar = True
    else:
        show_sidebar = False
    
    # pretty printing
    fields = Schema.get_predicates(dgraph_type)
    for key, v in data.items():
        if key in fields:
            try:
                if isinstance(fields[key], SingleChoice):
                    if isinstance(v, list):
                        data[key] = [fields[key].choices[subval] for subval in v]
                        data[key].sort()
                    else:
                        data[key] = fields[key].choices[v]
            except KeyError:
                pass
    
    review_actions = create_review_actions(current_user, data['uid'], data['entry_review_status'])
    return render_template('view/generic.html',
                            title=data.get('name'),
                            entry=data,
                            dgraph_type=dgraph_type,
                            review_actions=review_actions,
                            show_sidebar=show_sidebar)

@view.route("/query", methods=['GET', 'POST'])
def query():
    if request.args:
        filt = {'eq': {'entry_review_status': 'accepted'}}
        if not request.args.get('country', 'all') == 'all':
            uid = validate_uid(request.args.get('country'))
            if uid:
                filt.update({'uid_in': {'country': request.args.get('country')}})
        data = list_by_type(
            request.args['entity'], filt=filt)

        cols = []
        if data:
            for item in data:
                cols += item.keys()

        cols = list(set(cols))

        # CACHE THIS
        c_choices = get_country_choices(multinational=True)
        c_choices.insert(0, ('all', 'All'))
        form = SimpleQuery()
        form.country.choices = c_choices
        if request.args.get('country'):
            form.country.data = request.args.get('country')
        if request.args.get('entity'):
            form.entity.data = request.args.get('entity')
        return render_template('query_result.html', title='Query Result', result=data, cols=cols, show_sidebar=True, sidebar_title="Query", sidebar_form=form)
    return redirect(url_for('main.home'))


@view.route("/query/advanced")
def advanced_query():
    return render_template('not_implemented.html')


@view.route("/query/development/json")
@login_required
@requires_access_level(USER_ROLES.Admin)
def query_dev():
    query_string = build_query_string(request.args.to_dict(flat=False))

    result = dgraph.query(query_string)

    return jsonify(result['q'])



@view.route("/query/development", methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Admin)
def query_dev_result():
    if request.method == 'POST':
        r = request.form.to_dict(flat=False)
        r.pop('csrf_token')
        r.pop('submit')
        r = {k: v for k, v in r.items() if not v[0] == ''}
        return redirect(url_for("view.query_dev_result", **r))
    total = None
    pages = 1
    r = request.args.to_dict(flat=False)
    if len(r) > 0:
        query_string = build_query_string(r)
        if query_string:
            result = dgraph.query(query_string)
            total = result['total'][0]['count']

            max_results = int(request.args.get('_max_results', 25))
            # make sure no random values are passed in as parameters
            if not max_results in [10, 25, 50]: max_results = 25

            # fancy ceiling division
            pages = -(total // -max_results)

            result = result['q']

            # clean 'Entry' from types
            if len(result) > 0:
                for item in result:
                    if 'Entry' in item['dgraph.type']:
                        item['dgraph.type'].remove('Entry') 
    
    else: result = None

    from flaskinventory.flaskdgraph.query import generate_query_forms


    r_args = {k: v for k, v in request.args.to_dict(flat=False).items() if v[0] != ''}
    if '_page' in r_args:
        current_page = int(r_args.pop('_page')[0])
    else:
        current_page = 1

    form = generate_query_forms(dgraph_types=['Source', 'Organization', 'Tool'], populate_obj=r_args)

    return render_template("query/query_form.html", form=form, result=result, r_args=r_args, total=total, pages=pages, current_page=current_page)

@view.route("/query/development/form")
@login_required
@requires_access_level(USER_ROLES.Admin)
def query_dev_form():
    
    from flaskinventory.flaskdgraph.query import generate_query_forms

    form = generate_query_forms(dgraph_types=['Source', 'Organization', 'Tool'])

    return render_template("query/query_form.html", form=form)