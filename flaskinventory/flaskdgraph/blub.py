import json
import pydgraph

mutations = [
                {"set": [
                    {
                        'uid': 'uid(org)',
                        'publishes': [{'uid': 'uid(u)'}], 
                        'is_person': False, 
                        'entry_added': {'uid': '0x35b75'}, 
                        'entry_added|timestamp': '2021-08-26T16:52:41.008634+00:00', 
                        'entry_added|ip': '127.0.0.1', 
                        'entry_review_status': 'pending', 
                        'name': 'ZDF', 
                        'dgraph.type': 'Organization', 
                        'unique_name': 'zdf', 
                        'ownership_kind': 'public ownership',
                        'country': [
                            {'uid': 'uid(country)'}
                        ]
                    }, 
                    {
                        'uid': 'uid(u)', 
                        'dgraph.type': 'Source', 
                        'channel': {'uid': '0x35b6f'}, 
                        'other_names': ['ZDFfrontal', 'Frontal 21'], 
                        'related': [], 
                        'channel_url': 'zdffrontal', 
                        'name': 'zdffrontal', 
                        'audience_size': '2021-08-26',
                        'audience_size|followers': 32044, 
                        'founded': '2012-10-26T12:52:42', 
                        'verified_account': True, 
                        'contains_ads': 'no', 
                        'publication_kind': 'tv show', 
                        'special_interest': True, 
                        'topical_focus': ['society', 'politics'], 
                        'publication_cycle': 'continuous', 
                        'geographic_scope': 'national', 
                        'geographic_scope_countries': [{'uid': '0x35b89'}], 
                        'languages': ['de'], 
                        'unique_name': 'zdffrontal_twitter', 
                        'entry_added': {'uid': '0x35b75'}, 
                        'entry_added|timestamp': 
                        '2021-08-26T16:52:41.021773+00:00', 
                        'entry_added|ip': '127.0.0.1', 
                        'entry_review_status': 'pending'}
                    ]
                }
            ]
# upsert = {'query': query, "mutations": mutations}

query = '{ q1(func: uid(0x3a983)) { u as uid } q2(func: uid(0x3a982)) { org as uid } }'
query = None
del_nquads = None
cond = None

set_nquads = f''' 
                uid(org) <address_string> "Mainz" . 
                uid(org) <publishes> uid(u) .
                uid(u) <other_names> "Frontal" .
                '''

set_nquads = f'''
                _:user <dgraph.type> "User" .
                _:user <user_displayname> "Test Insert" .
                _:user <email> "test@upsert.com" .
                '''


client_stub = pydgraph.DgraphClientStub('localhost:9080')
client = pydgraph.DgraphClient(client_stub)
    
txn = client.txn()
mutation = txn.create_mutation(set_nquads=set_nquads, del_nquads=del_nquads, cond=cond)
request = txn.create_request(query=query, mutations=[
                                mutation], commit_now=True)

try:
    response = txn.do_request(request)
except Exception as e:
    print(e)
    response = False
finally:
    txn.discard()

print(response)

# import requests

# endpoint = "http://localhost:8080/mutate?commitNow=true"

# r = requests.post(endpoint, json=upsert)

# print(r.content)





# def parse_name(self):
#     if self.json.get('name'):
#         self.new_source['name'] = self.json.get('name')
#     else:
#         raise Exception(
#             'Invalid data! "name" not specified.')


#     if self.json.get('name'):
#         self.new_source['name'] = f'''{self.uids["new_source"]} <name> "{self.json.get("name")}" . '''




# def parse_channel(self):
#     try:
#         if self.json.get('channel_uid').startswith('0x'):
#             self.new_source['channel']['uid'] = self.json.get('channel_uid')
#     except Exception as e:
#         raise Exception(
#             f'Invalid data! uid of channel not defined: {e}')

#     if self.json.get('channel_uid').startswith('0x'):
#         self.new_source['channel'] = f'''{self.uids["new_source"]} <channel> "{self.json.get("channel_uid")}" . '''

#         self.set_nquards


def make_nquad(s, p, o, facets={}):
    facet_string = ""
    if len(facets) > 0:
        for facet, val in facets.items():
            facet_string += f''' {facet}="{val}" '''
        facet_string = '(' + facet_string + ') '
    return f'''{s} {p} {o} {facet_string} . '''

newsource = {'uid': 123}
newsource['nquads'] = [{'s': 1, 'p': 2, 'o': 3, "facets": facets}]