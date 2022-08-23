from flask import Blueprint, render_template, send_from_directory, current_app, request, url_for, make_response
from flaskinventory import dgraph
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.view.forms import SimpleQuery
from flaskinventory.main.model import Tool, Source

from datetime import datetime

main = Blueprint('main', __name__)


@main.route('/')
@main.route('/home')
def home():
    # needs caching!
    c_choices = get_country_choices()

    class Q(SimpleQuery):
        pass

    setattr(Q, 'used_for', Tool.used_for.query_field)
    form = Q()
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
    return render_template('main/imprint.html',
        title="Imprint")

@main.route('/privacy')
def privacy():
    return render_template('main/privacy.html',
        title="Privacy Policy")

@main.route('/notimplemented')
def under_development():
    return render_template('not_implemented.html')

@main.route('/guides/newssource')
def guides_newssource():
    return render_template('guides/newsource.html', show_sidebar=True,
        title="Guide for adding News Sources",
        meta_description="What is included in this inventory?")

@main.route('/guides/resources')
def guides_resources():
    return render_template('guides/resources.html', show_sidebar=True,
        title="Link Collection",
        meta_description="This is a collection of online resources that provide useful background and meta information on the media landscape in Europe. All resources are curated by the Meteor Team (WP3 of the OPTED Consortium) and the list is updated irregularly.")

@main.route('/guides/faq')
def guides_faq():
    return render_template('guides/faq.html', show_sidebar=True,
        title="FAQ",
        meta_description="Making entries to the inventory can sometimes be confusing. Therfore, we collected some frequently asked questions here. All questions are curated by the Meteor Team (WP3 of the OPTED Consortium) and the list is updated irregularly.")

@main.route('/guides/teaching-materials')
def guides_teaching():
    return render_template('guides/teaching.html', show_sidebar=True, 
        title="Teaching Materials",
        meta_description="Meteor is not only an inventory of news sources but can also serve as a tool for teaching courses at universities. The materials for this course are made available here and include: syllabus and slides.")


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


# Meta Tags

@main.app_context_processor
def meta_tags():
    return {'meta_url': url_for('main.home', _external=True),
            'meta_description': "OPTED Meteor (Media Text Open Registry) is an inventory for European journalistic texts and is part of the EU-funded Project OPTED where researchers work towards the creation of a new European research infrastructure for the study of political communication in Europe.",
            'meta_authors': ["Paul Balluff",  "Fabienne Lind", "Marvin Stecker", "Celina Dinhopl", "Hajo G. Boomgaarden", "Annie Waldherr"],
            'meta_keywords': 'News sources inventory; text as data; European Media Systems; open data; research infrastructure; Media in Europa; Political Texts; Automated Text Analysis',
            'meta_date_published': datetime.now(),
            'meta_date_modified': datetime.now()}
