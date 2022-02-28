from flask import (Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.view.dgraph import (get_dgraphtype, get_archive, get_channel, get_country,
                                        get_organization, get_paper, get_rejected, get_source, get_subunit, list_by_type, get_multinational)
from flaskinventory.view.utils import can_view, make_mini_table, make_results_table
from flaskinventory.view.forms import SimpleQuery
from flaskinventory.misc.forms import publication_kind_dict, topical_focus_dict
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.review.forms import ReviewActions
from flaskinventory.review.utils import create_review_actions

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
                        other_names: other_names
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
        c_choices = get_country_choices()
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
        uid = validate_uid(request.args.get('uid'))
        if not uid:
            return abort(404)
        dgraphtype = get_dgraphtype(uid)
        if dgraphtype:
            return redirect(url_for('view.view_' + dgraphtype.lower(), **request.args))
        else:
            return abort(404)
    else:
        return abort(404)


@view.route("/view/source/uid/<string:uid>")
@view.route("/view/source/<string:unique_name>")
def view_source(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_source(unique_name=unique_name, uid=uid)
    
    if unique_item:
        if "Source" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)
        if unique_item.get('audience_size'):
            unique_item['audience_size_table'] = make_mini_table(
                unique_item['audience_size'])

        # pretty print some fields
        if unique_item.get('publication_kind'):
            for i, item in enumerate(unique_item.get('publication_kind')):
                if item in publication_kind_dict.keys():
                    unique_item['publication_kind'][i] = publication_kind_dict[item]
        if unique_item.get('topical_focus'):
            for i, item in enumerate(unique_item.get('topical_focus')):
                if item in topical_focus_dict.keys():
                    unique_item['topical_focus'][i] = topical_focus_dict[item]

        related = unique_item.get('related', None)
        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/source.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               show_sidebar=True,
                               related=related,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/archive/<string:unique_name>")
@view.route("/view/archive/uid/<string:uid>")
def view_archive(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_archive(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Archive" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)
        
        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/archive.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/dataset/uid/<string:uid>")
@view.route("/view/dataset/<string:unique_name>")
def view_dataset(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_archive(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Dataset" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/archive.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/organization/<string:unique_name>")
@view.route("/view/organisation/<string:unique_name>")
@view.route("/view/organization/uid/<string:uid>")
@view.route("/view/organisation/uid/<string:uid>")
def view_organization(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_organization(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Organization" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)
        
        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/organization.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               show_sidebar=True,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/country/<string:unique_name>")
@view.route("/view/country/uid/<string:uid>")
def view_country(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_country(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Country" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
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
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_subunit(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Subunit" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/subunit.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/multinational/<string:unique_name>")
@view.route("/view/multinational/uid/<string:uid>")
def view_multinational(unique_name=None, uid=None):
    if uid:
        uid = validate_uid(uid)
        if not uid:
            return abort(404)
    unique_item = get_multinational(unique_name=unique_name, uid=uid)
    if unique_item:
        if "Multinational" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
            entry_type = unique_item.get('dgraph.type')[0]
            return redirect(url_for('view.view_' + entry_type.lower(), unique_name=unique_name))
        if not can_view(unique_item, current_user):
            return abort(403)

        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/multinational.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               review_actions=review_actions)
    else:
        return abort(404)


@view.route("/view/channel/<string:unique_name>")
def view_channel(unique_name):
    unique_item = get_channel(unique_name=unique_name)
    if unique_item:
        if "Channel" not in unique_item.get('dgraph.type'):
            unique_item['dgraph.type'].remove('Entry') if 'Entry' in unique_item['dgraph.type'] else None
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
    uid = validate_uid(uid)
    if not uid:
        return abort(404)
    unique_item = get_paper(uid)
    if unique_item:
        if "ResearchPaper" not in unique_item.get('dgraph.type'):
            return abort(404)
        if not can_view(unique_item, current_user):
            return abort(403)
        
        review_actions = create_review_actions(current_user, unique_item['uid'], unique_item['entry_review_status'])

        return render_template('view/paper.html',
                               title=unique_item.get('name'),
                               entry=unique_item,
                               review_actions=review_actions)
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

@view.route("/query", methods=['GET', 'POST'])
def query():
    if request.args:
        if request.args.get('country') == 'all':
            relation_filt = None
        else:
            uid = validate_uid(request.args.get('country'))
            if uid:
                relation_filt = {'country': {'uid': request.args.get('country')}}
            else:
                relation_filt = None
        data = list_by_type(
            request.args['entity'], relation_filt=relation_filt, filt={'eq': {'entry_review_status': 'accepted'}})

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
