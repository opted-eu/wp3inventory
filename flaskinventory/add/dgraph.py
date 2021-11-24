from flaskinventory import dgraph
from flaskinventory.auxiliary import icu_codes_list
from pydgraph import Txn
import json


async def generate_fieldoptions():

    query_channel = '''channel(func: type("Channel"), orderasc: name) { uid expand(_all_) }'''
    query_country = '''country(func: type("Country"), orderasc: name) @filter(eq(opted_scope, true)) { uid unique_name name  }'''
    query_dataset = '''dataset(func: type("Dataset"), orderasc: name) { uid unique_name name  }'''
    query_archive = '''archive(func: type("Archive"), orderasc: name) { uid unique_name name  }'''
    query_subunit = '''subunit(func: type("Subunit"), orderasc: name) { uid unique_name name other_names country{ name } }'''
    query_multinational = '''multinational(func: type("Multinational"), orderasc: name) { uid unique_name name other_names country{ name } }'''

    query_string = '{ ' + query_channel + query_country + \
        query_dataset + query_archive + query_subunit + query_multinational + ' }'

    # Use async query here because a lot of data is retrieved
    query_future = dgraph.connection.txn().async_query(query_string)
    res = Txn.handle_query_future(query_future)

    # data = dgraph.query(query_string)

    res = dgraph.connection.txn(read_only=True).query(query_string)
    data = json.loads(res.json, object_hook=dgraph.datetime_hook)

    data['language'] = icu_codes_list

    return data

def get_subunit_country(uid=None, country_code=None):
    if uid:
        query_string = f''' {{ q(func: uid({uid}))}} {{ country {{ uid }} }} '''
    if country_code:
        query_string = f''' {{ q(func: eq(country_code, "{country_code}")) 
                                @filter(type("Country")) {{
		                            uid }} }}'''
    
    result = dgraph.query(query_string)

    if len(result['q']) == 0:
        return False
    
    if uid:
        return result['q'][0]['country']['uid']
    
    if country_code:
        return result['q'][0]['uid']
        