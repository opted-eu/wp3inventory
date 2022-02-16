import asyncio
import json
from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory import dgraph
from flaskinventory.add.forms import NewEntry, NewMultinational, NewOrganization, NewArchive, NewDataset
from flaskinventory.add.dgraph import check_draft, get_draft, get_existing
from flaskinventory.add.sanitize import NewMultinationalSanitizer, SourceSanitizer, NewOrgSanitizer, NewArchiveSanitizer, NewDatasetSanitizer
from flaskinventory.edit.sanitize import EditDatasetSanitizer, EditOrgSanitizer, EditArchiveSanitizer
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.utils import requires_access_level
from flaskinventory.users.dgraph import list_entries
from flaskinventory.misc import get_ip
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
            elif form.entity.data == 'Organization':
                return redirect(url_for('add.new_organization'))
            elif form.entity.data == 'Archive':
                return redirect(url_for('add.new_archive'))
            elif form.entity.data == 'Dataset':
                return redirect(url_for('add.new_dataset'))
            else:
                return redirect(url_for('main.under_development'))

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


@add.route("/add/organisation", methods=['GET', 'POST'])
@add.route("/add/organization", methods=['GET', 'POST'])
@login_required
def new_organization(draft=None):
    form = NewOrganization(uid="_:neworganization", is_person='n')
    form.country.choices = get_country_choices(opted=False)

    if draft is None:
        draft = request.args.get('draft')
    if draft:
        draft = check_draft(draft, form)

    if form.validate_on_submit():
        if draft:
            try:
                sanitizer = EditOrgSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
                current_app.logger.debug(
                    f'Set Nquads: {sanitizer.delete_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Organization could not be updated: {e}', 'danger')
                return redirect(url_for('add.new_organization', draft=form.data))
        else:
            try:
                sanitizer = NewOrgSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Organization could not be added: {e}', 'danger')
                return redirect(url_for('add.new_organization'))

        try:
            if hasattr(sanitizer, 'delete_nquads'):
                delete = dgraph.upsert(
                    sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
                current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Organization has been added!', 'success')
            return redirect(url_for('view.view_organization', unique_name=sanitizer.new['unique_name']))
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'Organization could not be added: {e}', 'danger')
            return redirect(url_for('add.new_organization'))

    fields = list(form.data.keys())
    fields.remove('submit')
    fields.remove('csrf_token')
    return render_template('add/generic.html', title='Add Media Organization', form=form, fields=fields)


@add.route("/add/archive", methods=['GET', 'POST'])
@login_required
def new_archive(draft=None):
    form = NewArchive(uid="_:newarchive")

    if draft is None:
        draft = request.args.get('draft')
    if draft:
        draft = check_draft(draft, form)

    if form.validate_on_submit():
        if draft:
            try:
                sanitizer = EditArchiveSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
                current_app.logger.debug(
                    f'Set Nquads: {sanitizer.delete_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Archive could not be updated: {e}', 'danger')
                return redirect(url_for('add.new_archive', draft=form.data))
        else:
            try:
                sanitizer = NewArchiveSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Archive could not be added: {e}', 'danger')
                return redirect(url_for('add.new_archive'))

        try:
            if sanitizer.delete_nquads is not None:
                delete = dgraph.upsert(
                    sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
                current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Archive has been added!', 'success')
            return redirect(url_for('view.view_archive', unique_name=sanitizer.new['unique_name']))
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'Archive could not be added: {e}', 'danger')
            return redirect(url_for('add.new_archive'))

    fields = list(form.data.keys())
    fields.remove('submit')
    fields.remove('csrf_token')
    return render_template('add/generic.html', title='Add Full Text Archive', form=form, fields=fields)


@add.route("/add/dataset", methods=['GET', 'POST'])
@login_required
def new_dataset(draft=None):
    form = NewDataset(uid="_:newdataset")

    if draft is None:
        draft = request.args.get('draft')
    if draft:
        draft = check_draft(draft, form)

    if form.validate_on_submit():
        if draft:
            try:
                sanitizer = EditDatasetSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
                current_app.logger.debug(
                    f'Set Nquads: {sanitizer.delete_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Dataset could not be updated: {e}', 'danger')
                return redirect(url_for('add.new_dataset', draft=form.data))
        else:
            try:
                sanitizer = NewDatasetSanitizer(
                    form.data, current_user, get_ip())
                current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
            except Exception as e:
                if current_app.debug:
                    e_trace = traceback.format_exception(
                        None, e, e.__traceback__)
                    current_app.logger.debug(e_trace)
                flash(f'Dataset could not be added: {e}', 'danger')
                return redirect(url_for('add.new_dataset'))

        try:
            if sanitizer.delete_nquads is not None:
                delete = dgraph.upsert(
                    sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
                current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Dataset has been added!', 'success')
            return redirect(url_for('view.view_dataset', unique_name=sanitizer.new['unique_name']))
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'Dataset could not be added: {e}', 'danger')
            return redirect(url_for('add.new_dataset'))

    fields = list(form.data.keys())
    fields.remove('submit')
    fields.remove('csrf_token')
    return render_template('add/generic.html', title='Add Dataset', form=form, fields=fields)


@add.route("/add/multinational", methods=['GET', 'POST'])
@login_required
@requires_access_level(USER_ROLES.Admin)
def new_multinational():
    form = NewMultinational(uid="_:newcountry")

    if form.validate_on_submit():
        try:
            sanitizer = NewMultinationalSanitizer(
                form.data, current_user, get_ip())
            current_app.logger.debug(f'Set Nquads: {sanitizer.set_nquads}')
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(
                    None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'Multinational could not be added: {e}', 'danger')
            return redirect(url_for('add.new_multinational'))

        try:
            if sanitizer.delete_nquads is not None:
                delete = dgraph.upsert(
                    sanitizer.upsert_query, del_nquads=sanitizer.delete_nquads)
                current_app.logger.debug(delete)
            result = dgraph.upsert(None, set_nquads=sanitizer.set_nquads)
            current_app.logger.debug(result)
            flash(f'Multinational has been added!', 'success')
            return redirect(url_for('view.view_multinational', unique_name=sanitizer.new['unique_name']))
        except Exception as e:
            if current_app.debug:
                e_trace = traceback.format_exception(None, e, e.__traceback__)
                current_app.logger.debug(e_trace)
            flash(f'Multinational could not be added: {e}', 'danger')
            return redirect(url_for('add.new_multinational'))

    fields = list(form.data.keys())
    fields.remove('submit')
    fields.remove('csrf_token')
    return render_template('add/generic.html', title='Add Multinational', form=form, fields=fields)


@add.route("/add/confirmation")
def confirmation():
    return render_template("not_implemented.html")


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


