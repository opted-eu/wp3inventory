from flask import Blueprint, render_template, send_from_directory, current_app, request, url_for, make_response
from flaskinventory import dgraph
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.view.forms import SimpleQuery

from datetime import datetime

main = Blueprint('main', __name__)


@main.route('/')
@main.route('/home')
def home():
    # needs caching!
    c_choices = get_country_choices(multinational=True)
    c_choices.insert(0, ('all', 'All'))
    form = SimpleQuery()
    form.country.choices = c_choices

    query_string = '''{
                        data(func: has(dgraph.type), orderdesc: creation_date, first: 5) 
                            @filter(eq(entry_review_status, "accepted") AND has(creation_date)) {
                                uid
                                unique_name 
                                name 
                                dgraph.type 
                                title
                                creation_date
                                channel { name }
                                country { name }
                            }
                        }'''
    
    result = dgraph.query(query_string)
    for entry in result['data']:
        if 'Entry' in entry['dgraph.type']:
            entry['dgraph.type'].remove('Entry')
        if 'Resource' in entry['dgraph.type']:
            entry['dgraph.type'].remove('Resource')

    return render_template('home.html', form=form, recent=result['data'], show_sidebar=True)


@main.route('/about')
def about():
    return render_template('main/about.html', title="About Page", show_sidebar=True)

@main.route('/imprint')
def imprint():
    return render_template('main/imprint.html')

@main.route('/privacy')
def privacy():
    return render_template('main/privacy.html')

@main.route('/notimplemented')
def under_development():
    return render_template('not_implemented.html')

@main.route('/guides/newssource')
def guides_newssource():
    return render_template('guides/newsource.html', show_sidebar=True)

@main.route('/guides/resources')
def guides_resources():
    return render_template('guides/resources.html', show_sidebar=True)

@main.route('/guides/faq')
def guides_faq():
    return render_template('guides/faq.html', show_sidebar=True)

@main.route('/guides/teaching-materials')
def guides_teaching():
    return render_template('guides/teaching.html', show_sidebar=True)


# Misc Routes

@main.route('/robots.txt')
def static_from_root():
    return send_from_directory(current_app.static_folder, request.path[1:])

@main.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []

    lastmod = datetime.now().strftime('%Y-%m-%d')
    for rule in current_app.url_map.iter_rules():
        if 'GET' in rule.methods and len(rule.arguments) == 0 and rule.endpoint.startswith('main'):
            pages.append((url_for(rule.endpoint, _external=True), lastmod))

    sitemap_template = render_template('main/sitemap_template.xml', pages=pages)
    response = make_response(sitemap_template)
    response.headers['Content-Type'] = 'application/xml'
    return response