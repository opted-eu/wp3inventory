from flask import current_app
from flaskinventory import dgraph
from flaskinventory.auxiliary import icu_codes
import json


"""
    Inventory Detail View Functions
"""

def get_dgraphtype(uid):
    query_string = f'''{{ q(func: uid({uid})) {{  dgraph.type  }} }}'''

    data = dgraph.query(query_string)
    if len(data['q']) == 0:
        return False

    return data['q'][0]['dgraph.type'][0]


def get_source(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ source(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ source(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) { uid unique_name name entry_review_status user_displayname channel { name unique_name } }
                        published_by: ~publishes { name unique_name uid } 
                        archives: ~sources_included @facets @filter(type("Archive")) { name unique_name uid } 
                        datasets: ~sources_included @facets @filter(type("Dataset")) { name unique_name uid }
                        papers: ~sources_included @facets @filter(type("ResearchPaper")) { uid title published_date authors } 
                        } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['source']) == 0:
        return False

    data = data['source'][0]

    # split author names
    if data.get('papers'):
        for paper in data.get('papers'):
            if paper['authors'].startswith('['):
                paper['authors'] = paper['authors'].replace(
                    '[', '').replace(']', '').split(';')

    # flatten facets
    if data.get('channel_feeds'):
        tmp_list = []
        for key, item in data['channel_feeds|kind'].items():
            tmp_list.append(
                {'url': data['channel_feeds'][int(key)], 'kind': item})
        data['channel_feeds'] = tmp_list
        data.pop('channel_feeds|kind', None)
    if data.get('audience_size'):
        data = dgraph.flatten_date_facets(data, 'audience_size')
    if data.get('audience_residency'):
        data = dgraph.flatten_date_facets(data, 'audience_residency')

    # prettify language
    if data.get('languages'):
        data['languages_pretty'] = [icu_codes[language]
                                    for language in data['languages']]

    return data


def get_archive(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ archive(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ archive(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) num_sources: count(sources_included) } }'''

    query = query_func + query_fields
    data = dgraph.query(query)

    if len(data['archive']) == 0:
        return False

    data = data['archive'][0]

    return data


def get_organization(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ organization(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ organization(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name channel { name } }
                        owned_by: ~owns @filter(type(Organization)) { uid name unique_name } } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['organization']) == 0:
        return False

    data = data['organization'][0]

    return data


def get_channel(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ channel(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ channel(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) num_sources: count(~channel) } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['channel']) == 0:
        return False

    data = data['channel'][0]

    return data


def get_country(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ country(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ country(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) 
                        num_sources: count(~country @filter(type("Source")))  
                        num_orgs: count(~country @filter(type("Organization"))) } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['country']) == 0:
        return False

    data = data['country'][0]
    return data


def get_subunit(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ subunit(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ subunit(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name }
                        num_sources: count(~geographic_scope_subunit @filter(type("Source")))  
                        } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['subunit']) == 0:
        return False

    data = data['subunit'][0]
    return data


def get_multinational(unique_name=None, uid=None):
    if unique_name:
        query_func = f'{{ multinational(func: eq(unique_name, "{unique_name}"))'
    elif uid:
        query_func = f'{{ multinational(func: uid({uid}))'
    else:
        return None

    query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name }
                        num_sources: count(~country)
                        } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['multinational']) == 0:
        return False

    data = data['multinational'][0]
    return data


def get_paper(uid):
    query_func = f'{{ paper(func: uid({uid}))'

    query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name channel { name } } } }'''

    query = query_func + query_fields

    data = dgraph.query(query)

    if len(data['paper']) == 0:
        return False

    data = data['paper'][0]

    # split authors
    if data.get('authors'):
        if data['authors'].startswith('['):
            data['authors'] = data['authors'].replace(
                '[', '').replace(']', '').split(';')

    return data


def get_orphan(query):
    q_string = '''{
                source(func: eq(dgraph.type, "Source")) 
                @filter(not(has(~publishes))) {
                    uid
                    name
                    }
                }'''
    pass


""" 
    Query Related Functions 
"""

# List all entries of specified type, allows to pass in filters


def list_by_type(typename, filt=None, relation_filt=None, fields=None, normalize=False):
    query_head = f'{{ q(func: type("{typename}")) '
    if filt:
        query_head += dgraph.build_filt_string(filt)

    if fields == 'all':
        query_fields = " expand(_all_) "
    elif fields:
        query_fields = " ".join(fields)
    else:
        normalize = True
        if typename == 'Source':
            query_fields = ''' uid unique_name name founded
                                channel { name }
                                '''
        if typename == 'Organization':
            query_fields = ''' uid unique_name name founded
                                publishes: count(publishes)
                                owns: count(owns)
                                '''
        if typename in ['Archive', 'Dataset']:
            query_fields = ''' uid unique_name name access
                                sources_included: count(sources_included)
                                '''
        if typename == 'ResearchPaper':
            normalize = False
            query_fields = ''' uid title authors published_date journal
                                sources_included: count(sources_included)
                                '''
        if typename == 'Subunit':
            normalize = False
            query_fields = ''' uid name unique_name '''

    query_relation = ''
    if relation_filt:
        query_head += ' @cascade('
    
        for key, val in relation_filt.items():
            query_head += key
            query_relation += f'{key} {dgraph.build_filt_string(val)}'
            if fields == None:
                query_relation += f'{{ {key}: '
            else:
                query_relation += ' { '
            query_relation += ''' name }'''
        query_head += ')'
    else:
        query_fields += ''' country { country: name } '''

    if normalize:
        query_head += ''

    query_string = query_head + \
        ' { ' + query_fields + ' ' + query_relation + ' } }'

    data = dgraph.query(query_string)

    if len(data['q']) == 0:
        return False

    data = data['q']
    return data
