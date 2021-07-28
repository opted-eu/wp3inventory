from flaskinventory import dgraph
from flaskinventory.auxiliary import icu_codes_list

import json


def generate_fieldoptions():

    query_channel = '''channel(func: type("Channel")) { uid expand(_all_) }'''
    query_country = '''country(func: type("Country")) { uid unique_name name  }'''
    query_dataset = '''dataset(func: type("Dataset")) { uid unique_name name  }'''
    query_archive = '''archive(func: type("Archive")) { uid unique_name name  }'''
    query_subunit = '''subunit(func: type("Subunit")) { uid unique_name name other_names country{ name } }'''

    query_string = '{ ' + query_channel + query_country + \
        query_dataset + query_archive + query_subunit + ' }'

    res = dgraph.connection.txn(read_only=True).query(query_string)
    data = json.loads(res.json, object_hook=dgraph.datetime_hook)

    data['language'] = icu_codes_list

    return data
