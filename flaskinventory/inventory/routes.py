from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.inventory.dgraph import get_archive, get_channel, get_country, get_organization, get_paper, get_source, list_by_type
from flaskinventory.inventory.utils import make_mini_table, make_results_table
from flaskinventory.inventory.forms import SimpleQuery

inventory = Blueprint('inventory', __name__)


@inventory.route('/_quicksearch')
def quicksearch():
    query = request.args.get('q')
    # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
    query_string = f'''{{
            field1 as var(func: anyofterms(name, "{query}"))
            field2 as var(func: anyofterms(other_names, "{query}"))
            field3 as var(func: anyofterms(title, "{query}"))
            
            data(func: uid(field1, field2, field3)) 
                @normalize {{
                    uid 
                    unique_name: unique_name 
                    name: name 
                    type: dgraph.type 
                    title: title
                    channel {{ channel: name }}
                }}
            }}
    '''
    result = dgraph.query(query_string)
    result['status'] = True
    return jsonify(result)


@inventory.route('/search')
def search():
    query = request.args.get('query')
    # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
    query_string = f'''{{
            field1 as var(func: anyofterms(name, "{query}"))
            field2 as var(func: anyofterms(other_names, "{query}"))
            field3 as var(func: anyofterms(title, "{query}"))
            
            data(func: uid(field1, field2, field3)) 
                @normalize {{
                    uid 
                    unique_name: unique_name 
                    name: name 
                    type: dgraph.type 
                    title: title
                    channel {{ channel: name }}
                }}
            }}
    '''
    result = dgraph.query(query_string)
    result['status'] = True
    return jsonify(result)


@inventory.route("/view/source/uid/<string:uid>")
@inventory.route("/view/source/<string:unique_name>")
def view_source(unique_name=None, uid=None):
    if uid:
        unique_item = get_source(uid=uid)
    elif unique_name:
        unique_item = get_source(unique_name=unique_name)
    else:
        return abort(404)
    if unique_item:
        if "Source" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('inventory.view_' + entry_type.lower(), unique_name=unique_name))
        if unique_item.get('audience_size'):
            unique_item['audience_size_table'] = make_mini_table(
                unique_item['audience_size'])
        if unique_item.get('audience_residency'):
            unique_item['audience_residency_table'] = make_mini_table(
                unique_item['audience_residency'])
        related = unique_item.get('related', None)
 
        return render_template('view/source.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               show_sidebar=True,
                               related=related)
    else:
        return abort(404)


@inventory.route("/view/archive/<string:unique_name>")
def view_archive(unique_name):
    unique_item = get_archive(unique_name=unique_name)
    if unique_item:
        if "Archive" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('inventory.view_' + entry_type.lower(), unique_name=unique_name))

        return render_template('view/archive.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@inventory.route("/view/organisation/<string:unique_name>")
def view_organization(unique_name):
    unique_item = get_organization(unique_name=unique_name)
    if unique_item:
        if "Organization" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('inventory.view_' + entry_type.lower(), unique_name=unique_name))

        return render_template('view/organization.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@inventory.route("/view/country/<string:unique_name>")
def view_country(unique_name):
    unique_item = get_country(unique_name=unique_name)
    if unique_item:
        if "Country" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('inventory.view_' + entry_type.lower(), unique_name=unique_name))

        return render_template('view/country.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@inventory.route("/view/channel/<string:unique_name>")
def view_channel(unique_name):
    unique_item = get_channel(unique_name=unique_name)
    if unique_item:
        if "Channel" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('inventory.view_' + entry_type.lower(), unique_name=unique_name))

        return render_template('view/channel.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@inventory.route("/view/researchpaper/<string:uid>")
def view_researchpaper(uid):
    unique_item = get_paper(uid)
    if unique_item:
        if "ResearchPaper" not in unique_item.get('dgraph.type'):
            return abort(404)

        return render_template('view/paper.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@inventory.route("/query", methods=['GET', 'POST'])
def query():
    if request.args:
        if request.args.get('country') == 'all':
            relation_filt = None
        else:
            if request.args.get('entity') == 'source':
                relation_filt = {'geographic_scope_countries': {'uid': request.args.get('country')}}
            else:
                relation_filt = {'geographic_scope_countries': {'uid': request.args.get('country')}}
        data = list_by_type(
            request.args['entity'], relation_filt=relation_filt)

        if data:
            table = make_results_table(data)
        else:
            table = 'No results'

        # CACHE THIS
        countries = dgraph.query(
            '''{ q(func: type("Country")) { name uid } }''')

        c_choices = [(country.get('uid'), country.get('name'))
                     for country in countries['q']]
        c_choices = sorted(c_choices, key=lambda x: x[1])
        c_choices.insert(0, ('all', 'All'))
        form = SimpleQuery()
        form.country.choices = c_choices
        return render_template('query_result.html', title='Query Result', table=table, show_sidebar=True, sidebar_title="Query", sidebar_form=form)
    return redirect(url_for('main.home'))


@inventory.route("/query/advanced")
def advanced_query():
    return render_template('not_implemented.html')
