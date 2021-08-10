from flask import (current_app, Blueprint, render_template, url_for,
                   flash, redirect, request, abort, jsonify)
from flask_login import current_user, login_required
from flaskinventory.edit.forms import OrganizationForm
from flaskinventory.edit.utils import sanitize_edit_org

from flaskinventory import dgraph

edit = Blueprint('edit', __name__)


@edit.route('/edit/organisation/<string:unique_name>', methods=['GET', 'POST'])
@edit.route('/edit/organization/<string:unique_name>', methods=['GET', 'POST'])
@login_required
def edit_organization(unique_name):
    form = OrganizationForm()
    countries = dgraph.query('''{ q(func: type("Country")) { name uid } }''')
    c_choices = [(country.get('uid'), country.get('name'))
                 for country in countries['q']]
    c_choices = sorted(c_choices, key=lambda x: x[1])

    form.country.choices = c_choices
    if form.validate_on_submit():
        try:
            sanitize_edit_org(form.data)
            flash(f'Organization has been updated', 'success')
            return redirect(url_for('view.view_organization', unique_name=form.unique_name.data))
        except Exception as e:
            flash(f'Organization could not be updated: {e}', 'danger')
            return redirect(url_for('add.edit_organization', unique_name=form.unique_name.data))

    query_string = f'''{{ q(func: eq(unique_name, "{unique_name}")) {{
		uid expand(_all_) {{ unique_name uid }}
         }} }}'''

    result = dgraph.query(query_string)
    if result:
        for key, value in result['q'][0].items():
            if type(value) is list:
                if type(value[0]) is str:
                    value = ", ".join(value)
                elif key != 'country':
                    value_unique_name = ", ".join(
                        [subval['unique_name'] for subval in value])
                    value = ", ".join([subval['uid'] for subval in value])
                    setattr(getattr(form, key + '_unique_name'),
                            'data', value_unique_name)
            setattr(getattr(form, key), 'data', value)

        return render_template('edit/organization.html', title='Edit Organization', form=form)
    else:
        return abort(404)
