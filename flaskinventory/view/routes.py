from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.view.dgraph import get_dgraphtype, get_archive, get_channel, get_country, get_organization, get_paper, get_source, get_subunit, list_by_type
from flaskinventory.view.utils import can_view, make_mini_table, make_results_table
from flaskinventory.view.forms import SimpleQuery

view = Blueprint('view', __name__)


@view.route('/_quicksearch')
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
                    type: dgraph.type 
                    title: title
                    channel {{ channel: name }}
                }}
            }}
        '''
    result = dgraph.query(query_string, variables={'$name': query})
    result['status'] = True
    return jsonify(result)


@view.route('/search')
def search():
    if request.args.get('query'):
        query = request.args.get('query')
        # query_string = f'{{ data(func: regexp(name, /{query}/i)) @normalize {{ uid unique_name: unique_name name: name type: dgraph.type channel {{ channel: name }}}} }}'
        query_string = f'''
                query search($name: string)
                {{
                field1 as var(func: anyofterms(name, $name))
                field2 as var(func: anyofterms(other_names, $name))
                field3 as var(func: anyofterms(title, $name))
                
                data(func: uid(field1, field2, field3)) 
                    @normalize @filter(eq(entry_review_status, "accepted")) {{
                        uid 
                        unique_name: unique_name 
                        name: name 
                        type: dgraph.type 
                        title: title
                        channel {{ channel: name }}
                        country {{ country: name }}
                    }}
                }}
        '''
        result = dgraph.query(query_string, variables={'$name': query})

        if len(result['data']) > 0:
            result = result['data']
        else:
            result = None

        # CACHE THIS
        countries = dgraph.query(
            '''{ q(func: type("Country")) { name uid } }''')

        c_choices = [(country.get('uid'), country.get('name'))
                        for country in countries['q']]
        c_choices = sorted(c_choices, key=lambda x: x[1])
        c_choices.insert(0, ('all', 'All'))
        form = SimpleQuery()
        form.country.choices = c_choices
        return render_template('search_result.html', title='Query Result', result=result, show_sidebar=True, sidebar_title="Query", sidebar_form=form)
    else:
        flash("Please enter a search query in the top search bar", "info")
        return redirect(url_for('main.home'))

@view.route("/view")
def view_uid():
    if request.args.get('uid'):
        dgraphtype = get_dgraphtype(request.args.get('uid'))
        if dgraphtype:
            return redirect(url_for('view.view_' + dgraphtype.lower(), uid=request.args.get('uid')))
    else: return abort(404)


@view.route("/view/source/uid/<string:uid>")
@view.route("/view/source/<string:unique_name>")
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
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)
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


@view.route("/view/archive/<string:unique_name>")
@view.route("/view/archive/uid/<string:uid>")
def view_archive(unique_name=None, uid=None):
    unique_item = get_archive(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Archive" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/archive.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)

@view.route("/view/dataset/uid/<string:uid>")
@view.route("/view/dataset/<string:unique_name>")
def view_dataset(unique_name=None, uid=None):
    unique_item = get_archive(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Dataset" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/archive.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)

@view.route("/view/organization/<string:unique_name>")
@view.route("/view/organisation/<string:unique_name>")
@view.route("/view/organization/uid/<string:uid>")
@view.route("/view/organisation/uid/<string:uid>")
def view_organization(unique_name=None, uid=None):
    unique_item = get_organization(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Organization" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/organization.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@view.route("/view/country/<string:unique_name>")
def view_country(unique_name):
    unique_item = get_country(unique_name=unique_name)
    if unique_item:
        if "Country" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/country.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)

@view.route("/view/subunit/<string:unique_name>")
@view.route("/view/subunit/uid/<string:uid>")
def view_subunit(unique_name=None, uid=None):
    unique_item = get_subunit(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Subunit" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/subunit.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@view.route("/view/channel/<string:unique_name>")
def view_channel(unique_name):
    unique_item = get_channel(unique_name=unique_name)
    if unique_item:
        if "Channel" not in unique_item.get('dgraph.type'):
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)
        return render_template('view/channel.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@view.route("/view/researchpaper/<string:uid>")
def view_researchpaper(uid):
    unique_item = get_paper(uid)
    if unique_item:
        if "ResearchPaper" not in unique_item.get('dgraph.type'):
            return abort(404)
        if not can_view(unique_item, current_user):
            return abort(403)

        return render_template('view/paper.html',
                               title=unique_item.get('name'),
                               entry=unique_item)
    else:
        return abort(404)


@view.route("/query", methods=['GET', 'POST'])
def query():
    if request.args:
        if request.args.get('country') == 'all':
            relation_filt = None
        else:
            relation_filt = {'country': {'uid': request.args.get('country')}}
        data = list_by_type(
            request.args['entity'], relation_filt=relation_filt, filt={'eq': {'entry_review_status': 'accepted'}})

        cols = []
        if data:
            for item in data:
                cols += item.keys()
      
        cols = list(set(cols))

        # CACHE THIS
        countries = dgraph.query(
            '''{ q(func: type("Country")) { name uid } }''')

        c_choices = [(country.get('uid'), country.get('name'))
                     for country in countries['q']]
        c_choices = sorted(c_choices, key=lambda x: x[1])
        c_choices.insert(0, ('all', 'All'))
        form = SimpleQuery()
        form.country.choices = c_choices
        return render_template('query_result.html', title='Query Result', result=data, cols=cols, show_sidebar=True, sidebar_title="Query", sidebar_form=form)
    return redirect(url_for('main.home'))


@view.route("/query/advanced")
def advanced_query():
    return render_template('not_implemented.html')
