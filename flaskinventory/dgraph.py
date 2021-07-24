import json
import datetime
from dateutil.parser import isoparse
import os
import secrets

from flask import current_app, _app_ctx_stack, Markup
import pydgraph

from flaskinventory.users.constants import USER_ROLES
from flaskinventory.auxiliary import icu_codes, icu_codes_list


class DGraph(object):
    '''Class for dgraph database connection'''

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):

        app.config.setdefault('DGRAPH_ENDPOINT', 'localhost:9080')
        app.config.setdefault('DGRAPH_CREDENTIALS', None)
        app.config.setdefault('DGRAPH_OPTIONS', None)

        app.logger.info(
            f"Establishing connection to DGraph: {app.config['DGRAPH_ENDPOINT']}")

        self.client_stub = pydgraph.DgraphClientStub(app.config['DGRAPH_ENDPOINT'],
                                                     credentials=app.config['DGRAPH_CREDENTIALS'],
                                                     options=app.config['DGRAPH_OPTIONS'])

        self.client = pydgraph.DgraphClient(self.client_stub)

    ''' Connection Related Methods '''

    def close(self, *args):
        # Close each DGraph client stub
        self.client_stub.close()

    def teardown(self, exception):
        current_app.logger.info(
            f"Closing Connection: {current_app.config['DGRAPH_ENDPOINT']}")
        self.client_stub.close()

    ''' Static Methods '''

    # Helper function for parsing dgraph's iso strings
    @staticmethod
    def parse_datetime(s):
        try:
            # return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            return isoparse(s)
        except:
            return s

    # json decoder object_hook function
    @staticmethod
    def datetime_hook(obj):
        for k, v in obj.items():
            if isinstance(v, list):
                for i, s in enumerate(v):
                    obj[k][i] = DGraph.parse_datetime(s)
            if isinstance(v, str):
                obj[k] = DGraph.parse_datetime(v)
        return obj

    # flatten timeseries information embedded through facets
    @staticmethod
    def flatten_date_facets(data, field_name):
        tmp_list = []
        facet_keys = [item for item in data.keys(
        ) if item.startswith(field_name + '|')]
        facet_labels = [item.split('|')[1] for item in facet_keys]
        for index, value in enumerate(data[field_name]):
            tmp_dict = {'date': value}
            for facet, label in zip(facet_keys, facet_labels):
                tmp_dict[label] = data[facet][str(index)]
            tmp_list.append(tmp_dict)
        data[field_name] = tmp_list
        data[field_name + '_labels'] = facet_labels
        return data

    # Helper method for iterating over filter dictionaries
    @staticmethod
    def iter_filt_dict(filt_dict):
        for key, val in filt_dict.items():
            filt_string = f'{key}('
            if type(val) == dict:
                for subkey, subval in val.items():
                    filt_string += f'{subkey}, "{subval}")'
            else:
                filt_string += f'{val})'
        return filt_string

    # Helper Method for building complex query filter strings
    @staticmethod
    def build_filt_string(filt, operator="AND"):
        if type(filt) == str:
            return filt
        elif type(filt) == dict:
            return f'@filter({DGraph.iter_filt_dict(filt)})'
        elif type(filt) == list:
            filt_string = f" {operator} ".join(
                [DGraph.iter_filt_dict(item) for item in filt])
            return f'@filter({filt_string})'
        else:
            return ''

    """    
    Generic Query Methods 
    """

    def query(self, query_string, variables=None):
        current_app.logger.debug(f"Sending dgraph query: {query_string}")
        if variables is None:
            res = self.client.txn(read_only=True).query(query_string)
        else:
            res = self.client.txn(read_only=True).query(
                query_string, variables=variables)
        current_app.logger.debug(f"Received response for dgraph query.")
        data = json.loads(res.json, object_hook=self.datetime_hook)
        return data

    def get_uid(self, field, value):
        query_string = f'{{ q(func: eq({field}, {value})) {{ uid {field} }} }}'
        data = self.query(query_string)
        if len(data['q']) == 0:
            return None
        return data['q'][0]['uid']

    """
        New Entries
    """

    def mutation(self, data):
        # if type(data) is not dict or type(data) is not list:
        #     raise TypeError()

        txn = self.client.txn()

        try:
            response = txn.mutate(set_obj=data)
            txn.commit()
        except Exception as e:
            current_app.logger.error(e)
            response = False
        finally:
            txn.discard()

        if response:
            return response
        else:
            return False

    

    """ 
        User Related Methods 
    """

    def get_user(self, **kwargs):

        uid = kwargs.get('uid', None)
        email = kwargs.get('email', None)

        if uid:
            query_func = f'{{ q(func: uid({uid}))'
        elif email:
            query_func = f'{{ q(func: eq(email, "{email}"))'
        else:
            raise ValueError()

        query_fields = f'{{ uid email pw_reset @facets user_displayname user_orcid date_joined user_role user_affiliation }} }}'
        query_string = query_func + query_fields
        data = self.query(query_string)
        if len(data['q']) == 0:
            return None
        data = data['q'][0]
        return data

    def user_login(self, email, pw):
        query_string = f'{{login_attempt(func: eq(email, "{email}")) {{ checkpwd(pw, {pw}) }} }}'
        result = self.query(query_string)
        if len(result['login_attempt']) == 0:
            return 'Invalid Email'
        else:
            return result['login_attempt'][0]['checkpwd(pw)']

    def create_user(self, user_data, invited_by=None):
        if type(user_data) is not dict:
            raise TypeError()

        if invited_by:
            user_data['invited_by'] = {'uid': invited_by,
                                       'invited_by|date': datetime.datetime.now(datetime.timezone.utc).isoformat()}

        user_data['uid'] = '_:newuser'
        user_data['dgraph.type'] = 'User'
        user_data['user_role'] = USER_ROLES.User
        user_data['user_displayname'] = secrets.token_urlsafe(6)
        user_data['date_joined'] = datetime.datetime.now(
            datetime.timezone.utc).isoformat()

        txn = self.client.txn()

        try:
            response = txn.mutate(set_obj=user_data)
            txn.commit()
        except:
            response = False
        finally:
            txn.discard()

        if response:
            return response.uids['newuser']
        else:
            return False

    def list_users(self):
        data = self.query('{ q(func: type("User")) { uid expand(_all_) } }')
        if len(data['q']) == 0:
            return False
        return data['q']

    """
        Inventory Detail View Methods
    """

    def get_source(self, unique_name=None, uid=None):
        if unique_name:
            query_func = f'{{ source(func: eq(unique_name, "{unique_name}"))'
        elif uid:
            query_func = f'{{ source(func: uid({uid}))'
        else:
            return None

        query_fields = '''{ uid dgraph.type expand(_all_)  { uid unique_name name channel { name } }
                            published_by: ~publishes { name unique_name uid } 
                            archives: ~sources_included @facets @filter(type("Archive")) { name unique_name uid } 
                            papers: ~sources_included @facets @filter(type("ResearchPaper")) { uid title published_date authors } } }'''

        query = query_func + query_fields

        res = self.client.txn(read_only=True).query(query)

        data = json.loads(res.json, object_hook=self.datetime_hook)
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
            data = self.flatten_date_facets(data, 'audience_size')
        if data.get('audience_residency'):
            data = self.flatten_date_facets(data, 'audience_residency')

        # prettify language
        if data.get('languages'):
            data['languages_pretty'] = [icu_codes[language]
                                        for language in data['languages']]

        return data

    def get_archive(self, unique_name=None, uid=None):
        if unique_name:
            query_func = f'{{ archive(func: eq(unique_name, "{unique_name}"))'
        elif uid:
            query_func = f'{{ archive(func: uid({uid}))'
        else:
            return None

        query_fields = '''{ uid dgraph.type expand(_all_) num_sources: count(sources_included) } }'''

        query = query_func + query_fields
        res = self.client.txn(read_only=True).query(query)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['archive']) == 0:
            return False

        data = data['archive'][0]

        return data

    def get_organization(self, unique_name=None, uid=None):
        if unique_name:
            query_func = f'{{ organization(func: eq(unique_name, "{unique_name}"))'
        elif uid:
            query_func = f'{{ organization(func: uid({uid}))'
        else:
            return None

        query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name channel { name } }
    	                    owned_by: ~owns { uid	name unique_name } } }'''

        query = query_func + query_fields

        res = self.client.txn(read_only=True).query(query)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['organization']) == 0:
            return False

        data = data['organization'][0]

        return data

    def get_channel(self, unique_name=None, uid=None):
        if unique_name:
            query_func = f'{{ channel(func: eq(unique_name, "{unique_name}"))'
        elif uid:
            query_func = f'{{ channel(func: uid({uid}))'
        else:
            return None

        query_fields = '''{ uid dgraph.type expand(_all_) num_sources: count(~channel) } }'''

        query = query_func + query_fields

        res = self.client.txn(read_only=True).query(query)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['channel']) == 0:
            return False

        data = data['channel'][0]

        return data

    def get_country(self, unique_name=None, uid=None):
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

        res = self.client.txn(read_only=True).query(query)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['country']) == 0:
            return False

        data = data['country'][0]
        return data

    def get_paper(self, uid):
        query_func = f'{{ paper(func: uid({uid}))'

        query_fields = '''{ uid dgraph.type expand(_all_) { uid name unique_name channel { name } } } }'''

        query = query_func + query_fields

        res = self.client.txn(read_only=True).query(query)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['paper']) == 0:
            return False

        data = data['paper'][0]

        # split authors
        if data.get('authors'):
            if data['authors'].startswith('['):
                data['authors'] = data['authors'].replace(
                    '[', '').replace(']', '').split(';')

        return data

    def get_orphan(self, query):
        q_string = '''{
                    source(func: eq(dgraph.type, "Source")) 
                    @filter(not(has(~publishes))) {
                        uid
                        name
                     }
                    }'''
        pass

    """ 
        Query Related Methods 
    """

    # List all entries of specified type, allows to pass in filters
    def list_by_type(self, typename, filt=None, relation_filt=None, fields=None, normalize=False):
        query_head = f'{{ q(func: type("{typename}")) '
        if filt:
            query_head += self.build_filt_string(filt)

        if fields == 'all':
            query_fields = " expand(_all_) "
        elif fields:
            query_fields = " ".join(fields)
        else:
            normalize = True
            if typename == 'Source':
                query_fields = ''' uid: uid unique_name: unique_name name: name founded: founded
                                    channel { channel: name }
                                    '''
            if typename == 'Organization':
                query_fields = ''' uid: uid unique_name: unique_name name: name founded: founded
                                    publishes: count(publishes)
                                    owns: count(owns)
                                    '''
            if typename == 'Archive':
                query_fields = ''' uid: uid unique_name: unique_name name: name access: access
                                    sources_included: count(sources_included)
                                    '''
            if typename == 'ResearchPaper':
                normalize = False
                query_fields = ''' uid title authors published_date journal
                                    sources_included: count(sources_included)
                                    '''

        query_relation = ''
        if relation_filt:
            query_head += ' @cascade '
            if 'Country' in relation_filt.keys() and fields is None:
                query_fields += ''' country { country: name } '''

            for key, val in relation_filt.items():
                query_relation += f'{key} {self.build_filt_string(val)}'
                if fields == None:
                    query_relation += f'{{ {key}: '
                else:
                    query_relation += ' { '
                query_relation += ''' name }'''
        else:
            query_fields += ''' country { country: name } '''

        if normalize:
            query_head += '@normalize'

        query_string = query_head + \
            ' { ' + query_fields + ' ' + query_relation + ' } }'

        res = self.client.txn(read_only=True).query(query_string)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        if len(data['q']) == 0:
            return False

        data = data['q']
        return data

    def generate_fieldoptions(self):

        query_channel = '''channel(func: type("Channel")) { uid expand(_all_) }'''
        query_country = '''country(func: type("Country")) { uid unique_name name  }'''
        query_dataset = '''dataset(func: type("Dataset")) { uid unique_name name  }'''
        query_archive = '''archive(func: type("Archive")) { uid unique_name name  }'''
        query_subunit = '''subunit(func: type("Subunit")) { uid unique_name name country { name } }'''

        query_string = '{ ' + query_channel + query_country + query_dataset + query_archive + query_subunit + ' }'

        res = self.client.txn(read_only=True).query(query_string)
        data = json.loads(res.json, object_hook=self.datetime_hook)

        data['language'] = icu_codes_list

        return data

    """ 
        Misc Methods (unused)
    """

    def update_entry(self, uid, input_data):
        if type(input_data) is not dict:
            raise TypeError()

        input_data['uid'] = uid

        txn = self.client.txn()

        try:
            response = txn.mutate(set_obj=input_data)
            txn.commit()
        except:
            response = False
        finally:
            txn.discard()

        if response:
            return True
        else:
            return False

    def delete_entry(self, uid):

        mutation = {'uid': uid}
        txn = self.client.txn()

        try:
            response = txn.mutate(del_obj=mutation)
            txn.commit()
        except:
            response = False
        finally:
            txn.discard()

        if response:
            return True
        else:
            return False
