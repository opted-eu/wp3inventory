
from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.flaskdgraph.schema import Schema
from flaskinventory.main.model import Organization
from flaskinventory.add.forms import NewEntry, AutoFill
from flaskinventory.add.dgraph import check_draft, get_draft, get_existing
from flaskinventory.main.sanitizer import Sanitizer
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.utils import requires_access_level
from flaskinventory.users.dgraph import list_entries
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.flaskdgraph.utils import strip_query, validate_uid
import traceback

add = Blueprint('add', __name__)


@add.route("/add", methods=['GET', 'POST'])
@login_required
def new_entry():
    form = NewEntry()
    if form.validate_on_submit():
        query = strip_query(form.name.data)
        query_string = f'''{{
                field1 as var(func: regexp(name, /{query.ljust(3)}/i)) @filter(type("{form.entity.data}"))
                field2 as var(func: allofterms(name, "{query}")) @filter(type("{form.entity.data}"))
                field3 as var(func: allofterms(other_names, "{query}")) @filter(type("{form.entity.data}"))
    
                data(func: uid(field1, field2, field3)) {{
                    uid
                    expand(_all_) {{ name }}
                    }}
                }}
        '''
        result = dgraph.query(query_string)
        if len(result['data']) > 0:
            return render_template('add/database_check.html', query=form.name.data, result=result['data'], entity=form.entity.data)
            # return redirect(url_for('add.database_check', result=result['data']))
        else:
            if form.entity.data == 'Source':
                return redirect(url_for('add.new_source', entry_name=form.name.data))
            else:
                return redirect(url_for('add.new', dgraph_type=form.entity.data))

    drafts = list_entries(current_user.id, onlydrafts=True)
    if drafts:
        drafts = drafts[0]['drafts']
    return render_template('add/newentry.html', form=form, drafts=drafts)


@add.route("/add/source")
@login_required
def new_source():
    draft = request.args.get('draft')
    existing = request.args.get('existing')

    draft = validate_uid(draft)
    existing = validate_uid(existing)
    if draft:
        draft = get_draft(draft)
    elif existing:
        existing = get_existing(existing)
    
    return render_template("add/newsource.html", draft=draft, existing=existing)


@login_required
@add.route("/add/draft/<string:entity>/<string:uid>")
@add.route("/add/draft/")
def from_draft(entity=None, uid=None):
    if entity and uid:
        if entity == 'Source':
            return redirect(url_for('add.new_source', draft=uid))
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
        return redirect(url_for('add.new_source', draft=result['q'][0]['drafts'][0]['uid']))
    else:
        return redirect(url_for('add.new_entry'))



@add.route("/add/<string:dgraph_type>", methods=['GET', 'POST'])
@add.route("/add/<string:dgraph_type>/draft/<string:draft>", methods=['GET', 'POST'])
@login_required
def new(dgraph_type=None, draft=None):
    if not dgraph_type:
        return abort(404)
    dgraph_type = dgraph_type.title()

    form = Schema.generate_new_entry_form(dgraph_type=dgraph_type)
    
    if draft is None:
        draft = request.args.get('draft')
    if draft:
        draft = check_draft(draft, form)

    if form.validate_on_submit():
        if draft:
            try:
                sanitizer = Sanitizer.edit(form.data, dgraph_type=dgraph_type)
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'{dgraph_type} could not be updated: {e}', 'danger')
                return redirect(url_for('add.new', dgraph_type=dgraph_type, draft=form.data))
        else:
            try:
                sanitizer = Sanitizer(form.data, dgraph_type=dgraph_type)
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'{dgraph_type} could not be added: {e}', 'danger')
                return redirect(url_for('add.new', dgraph_type=dgraph_type))

        try:
            if sanitizer.is_upsert:
                result = dgraph.upsert(sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads, set_nquads=sanitizer.set_nquads)
            else:
                result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            flash(f'{dgraph_type} has been added!', 'success')
            if sanitizer.is_upsert:
                uid = str(sanitizer.entry_uid)
            else:
                newuids = dict(result.uids)
                uid = newuids[str(sanitizer.entry_uid).replace('_:', '')]
            return redirect(url_for('view.uid', uid=uid))
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'{dgraph_type} could not be added: {e}', 'danger')
            return redirect(url_for('add.new', dgraph_type=dgraph_type))

    fields = list(form.data.keys())
    fields.remove('submit')
    fields.remove('csrf_token')

    if dgraph_type in ['Tool', 'ResearchPaper', 'Dataset', 'Corpus']:
        show_sidebar = True
        sidebar_items = {'autofill': AutoFill()}
    else:
        show_sidebar = False
        sidebar_items = {}

    return render_template('add/generic.html', title=f'Add {dgraph_type}', form=form, fields=fields, show_sidebar=show_sidebar, sidebar_items=sidebar_items)
