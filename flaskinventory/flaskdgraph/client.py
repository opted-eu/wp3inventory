import json
from dateutil.parser import isoparse
from flask import current_app, _app_ctx_stack
import pydgraph
import logging

class DGraph(object):
    """
        Class for dgraph database connection
    """

    _client = None

    def __init__(self, app=None):

        self.logger = logging.getLogger(__name__)

        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):

        app.config.setdefault('DGRAPH_ENDPOINT', 'localhost:9080')
        app.config.setdefault('DGRAPH_CREDENTIALS', None)
        app.config.setdefault('DGRAPH_OPTIONS', None)
        app.teardown_appcontext(self.teardown)

    """ 
        Connection Related Methods
    """

    @property
    def connection(self):
        # ctx = _app_ctx_stack.top
        # if ctx is not None:
        #     if not hasattr(ctx, 'dgraph'):
        #         ctx.dgraph = self.connect()
        #     return ctx.dgraph
        if self._client is None:
            self._client = self.connect()
        return self._client

    def connect(self):
        self.logger.debug(
            f"Establishing connection to DGraph: {current_app.config['DGRAPH_ENDPOINT']}")

        self.client_stub = pydgraph.DgraphClientStub(current_app.config['DGRAPH_ENDPOINT'],
                                                     credentials=current_app.config['DGRAPH_CREDENTIALS'],
                                                     options=current_app.config['DGRAPH_OPTIONS'])

        return pydgraph.DgraphClient(self.client_stub)

    def close(self, *args):
        # Close each DGraph client stub
        self.client_stub.close()

    def teardown(self, exception):
        ctx = _app_ctx_stack.top
        if hasattr(ctx, 'dgraph'):
            self.logger.info(
                f"Closing Connection: {current_app.config['DGRAPH_ENDPOINT']}")
            self.client_stub.close()

    ''' Static Methods '''

    # Helper function for parsing dgraph's iso strings
    @staticmethod
    def parse_datetime(s):
        if type(s) == str:
            if len(s) <= 4:
                return s
        try:
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
        self.logger.debug(f"Sending dgraph query: {query_string}")
        if variables is None:
            res = self.connection.txn(read_only=True).query(query_string)
        else:
            self.logger.debug(f"Got the following variables {variables}")
            res = self.connection.txn(read_only=True).query(
                query_string, variables=variables)
        self.logger.debug(f"Received response for dgraph query.")
        data = json.loads(res.json, object_hook=self.datetime_hook)
        return data

    def get_uid(self, field, value):
        query_string = f'''
            query quicksearch($value: string)
            {{ q(func: eq({field}, $value)) {{ uid {field} }} }}'''
        data = self.query(query_string, variables={'$value': value})
        if len(data['q']) == 0:
            return None
        return data['q'][0]['uid']

    def get_unique_name(self, uid):
        query_string = f'{{ q(func: uid({uid})) @filter(has(dgraph.type)) {{ uid unique_name }} }}'
        data = self.query(query_string)
        if len(data['q']) == 0:
            return None
        return data['q'][0]['unique_name']

    def get_dgraphtype(self, uid: str, clean: list =['Entry', 'Resource']):
        query_string = f'''{{ q(func: uid({uid})) @filter(has(dgraph.type)) {{  dgraph.type  }} }}'''

        data = self.query(query_string)
        if len(data['q']) == 0:
            return False
        if 'User' in data['q'][0]['dgraph.type']:
            return False
        
        if len(clean) > 0:
            for item in clean:
                if item in data['q'][0]['dgraph.type']:
                    data['q'][0]['dgraph.type'].remove(item)
            return data['q'][0]['dgraph.type'][0]
        else:
            return data['q'][0]['dgraph.type']

    """
        New Entries
    """

    def mutation(self, data):
        # if type(data) is not dict or type(data) is not list:
        #     raise TypeError()

        txn = self.connection.txn()

        try:
            response = txn.mutate(set_obj=data)
            txn.commit()
        except Exception as e:
            self.logger.error(e)
            response = False
        finally:
            txn.discard()

        if response:
            return response
        else:
            return False

    """
        Update Methods
    """

    def update_entry(self, input_data, uid=None):
        self.logger.debug("Performing mutation:")
        self.logger.debug(input_data)
        if type(input_data) is not dict:
            raise TypeError()

        if uid:
            input_data['uid'] = str(uid)

        txn = self.connection.txn()

        try:
            response = txn.mutate(set_obj=input_data)
            txn.commit()
        except Exception as e:
            self.logger.warning(e)
            response = False
        finally:
            txn.discard()

        if response:
            return True
        else:
            return False

    def upsert(self, query, set_nquads=None, del_nquads=None, cond=None):
        if query:
            if not query.startswith('{'):
                query = '{' + query + '}'
        self.logger.debug("Performing upsert:")
        self.logger.debug(f'Query:\n{query}')
        self.logger.debug(f'set nquads:\n{set_nquads}')
        self.logger.debug(f'delete nquads:\n{del_nquads}')
        txn = self.connection.txn()
        mutation = txn.create_mutation(set_nquads=set_nquads, del_nquads=del_nquads, cond=cond)
        request = txn.create_request(query=query, mutations=[
                                     mutation], commit_now=True)

        try:
            response = txn.do_request(request)
        except Exception as e:
            self.logger.warning(e)
            response = False
        finally:
            txn.discard()

        if response:
            self.logger.debug(f'Response: {response}')
            return response
        else:
            self.logger.debug(f'No Response')
            return False

    def delete(self, mutation):

        txn = self.connection.txn()

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
