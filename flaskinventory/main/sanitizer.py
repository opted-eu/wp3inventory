from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.dgraph_types import (UID, MutualRelationship, NewID, Predicate, ReverseRelationship, Scalar,
                                        SingleRelationship, GeoScalar, Variable, make_nquad, dict_to_nquad)
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.add.external import (geocode, instagram,
                                         parse_meta, siterankdata, find_sitemaps, find_feeds,
                                         build_url, twitter, facebook, get_wikidata)
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.dgraph import User
from flaskinventory import dgraph
from flask import current_app

from flaskinventory.main.model import Entry, Organization
from flaskinventory.misc import get_ip
from flask_login import current_user

# External Utilities

from slugify import slugify
import secrets

import datetime
from dateutil import parser as dateparser


class Sanitizer:
    """ Base Class for validating data and generating mutation object
        Validates all predicates from dgraph type 'Entry'
        also keeps track of user & ip address.
        Relevant return attributes are upsert_query (string), set_nquads (string), delete_nquads (string)
    """

    upsert_query = None

    def __init__(self, data: dict, fields: dict = None, **kwargs):

        self.user = current_user
        self.user_ip = get_ip()
        self._validate_inputdata(data, self.user, self.user_ip)
        self.fields = fields or Entry.predicates()

        if self.user.user_role < USER_ROLES.Contributor:
            raise InventoryPermissionError

        self.data = data

        self.is_upsert = kwargs.get('is_upsert', False)
        self.skip_keys = kwargs.get('skip_keys', [])
        self.overwrite = {}
        self.newsubunits = []

        self.entry = {}
        self.related_entries = []
        self.facets = {}
        self.entry_uid = None
        self._parse()
        self.process_related()

    @staticmethod
    def _validate_inputdata(data: dict, user: User, ip: str) -> bool:
        if not isinstance(data, dict):
            raise TypeError('Data object has to be type dict!')
        if not isinstance(user, User):
            raise InventoryPermissionError('User Object is not class User!')
        if not isinstance(ip, str):
            raise TypeError('IP Address is not string!')
        return True

    @classmethod
    def edit(cls, data: dict, **kwargs):
        cls._validate_inputdata(data, current_user, get_ip())

        if 'uid' not in data.keys():
            raise InventoryValidationError(
                'You cannot edit an entry without a UID')

        check = cls._check_entry(data['uid'])
        if not check:
            raise InventoryValidationError(
                f'Entry can not be edited! UID does not exist: {data["uid"]}')

        if current_user.user_role < USER_ROLES.Reviewer:
            if check.get('entry_added').get('uid') != current_user.id:
                raise InventoryPermissionError(
                    'You do not have the required permissions to edit this entry!')

        return cls(data, is_upsert=True, **kwargs)

    @property
    def set_nquads(self):
        nquads = dict_to_nquad(self.entry)
        return " \n".join(nquads)

    @property
    def delete_nquads(self):
        if self.is_upsert:
            # for upserts, we first have to delete all list type predicates
            # otherwise, the user cannot remove relationships, but just add to them
            del_obj = []

            for key, val in self.overwrite.items():
                for predicate in list(set(val)):
                    del_obj.append({'uid': key, predicate: '*'})

            nquads = [" \n".join(dict_to_nquad(obj)) for obj in del_obj]
            return " \n".join(nquads)

        return None

    @staticmethod
    def _check_entry(uid):
        query = f'''{{ q(func: uid({uid})) @filter(has(dgraph.type))'''
        query += "{ unique_name dgraph.type entry_review_status entry_added { uid } } }"
        data = dgraph.query(query)

        if len(data['q']) == 0:
            return False

        return data['q'][0]

    def _add_entry_meta(self, entry, newentry=False):
        # verify that dgraph.type is not added to self if the entry already exists
        if newentry:
            if entry.get('dgraph.type'):
                if type(entry['dgraph.type']) != list:
                    entry['dgraph.type'] = [entry['dgraph.type']]
                entry['dgraph.type'].append(
                    'Entry') if 'Entry' not in entry['dgraph.type'] else None
            else:
                entry['dgraph.type'] = ["Entry"]

        facets = {'timestamp': datetime.datetime.now(
            datetime.timezone.utc),
            'ip': self.user_ip}
        if not newentry:
            entry['entry_edit_history'] = UID(self.user.uid, facets=facets)
        else:
            entry['entry_added'] = UID(self.user.uid, facets=facets)
            entry['entry_review_status'] = 'pending'
            entry['creation_date'] = datetime.datetime.now(
                datetime.timezone.utc)

        return entry

    def _preprocess_facets(self):
        # helper function to sieve out facets from the input data
        # currently only supports single facets
        for key in self.data.keys():
            if '|' in key:
                predicate, facet = key.split('|')
                self.facets[predicate] = {facet: self.data[key]}
                

    def _parse(self):
        if self.data.get('uid'):
            uid = self.data.pop('uid')
            self.entry_uid = self.fields['uid'].validate(uid)
        else:
            self.entry_uid = self.fields['uid'].default
        
        self.entry['uid'] = self.entry_uid
        self.skip_keys.append(self.fields['uid'].predicate)

        self._preprocess_facets()

        for item in dir(self):
            if item.startswith('parse_'):
                m = getattr(self, item)
                if callable(m):
                    m()

        for key, item in self.fields.items():
            validated = None
            if key in self.skip_keys: continue

            if key in self.facets.keys():
                facets = self.facets[key]
            else:
                facets = None
            
            if self.data.get(key) and isinstance(item, ReverseRelationship):
                validated = item.validate(self.data[key], self.entry_uid, facets=facets)
                if isinstance(validated, list):
                    self.related_entries += validated
                else:
                    self.related_entries.append(validated)
                continue
            elif self.data.get(key) and isinstance(item, MutualRelationship):
                node_data, data_node = item.validate(self.data[key], self.entry_uid, facets=facets)
                self.entry[item.predicate] = node_data
                if isinstance(data_node, list):
                    self.related_entries += data_node
                else:
                    self.related_entries.append(data_node)
                continue
            
            elif self.data.get(key) and isinstance(item, SingleRelationship):
                related_items = item.validate(self.data[key], facets=facets)
                validated = []
                if isinstance(related_items, list):
                    for item in related_items:
                        validated.append(item['uid'])
                        if isinstance(item['uid'], NewID):
                            self.related_entries.append(item)
                        
                else:
                    validated = related_items['uid']
                    if isinstance(related_items['uid'], NewID):
                        self.related_entries.append(related_items)                

            elif self.data.get(key) and hasattr(item, 'validate'):
                validated = item.validate(self.data[key], facets=facets)  
            elif hasattr(item, 'autocode'):
                if item.autoinput in self.data.keys():
                    validated = item.autocode(self.data[item.autoinput], facets=facets)        
            elif hasattr(item, 'default'):
                validated = item.default
                if hasattr(validated, 'facets') and facets is not None:
                    validated.update_facets(facets)

        
            if validated is None: continue

            if type(validated) == dict:
                self.entry.update(validated)
            elif type(validated) == list and key in self.entry.keys():
                self.entry[key] += validated
            elif type(validated) == set and key in self.entry.keys():
                self.entry[key] = set.union(validated, self.entry[key])
            else:
                self.entry[key] = validated

            if hasattr(item, 'allow_new'):
                if item.allow_new:
                    print('generate unique name for new item')

        if self.is_upsert:
            self.entry = self._add_entry_meta(self.entry)
            self.overwrite[self.entry_uid] = [item.predicate for _, item in self.fields.items() if item.overwrite]
        else:
            self.generate_unique_name()
            self.entry = self._add_entry_meta(self.entry, newentry=True)

    def process_related(self):
        for related in self.related_entries:
            related = self._add_entry_meta(related, newentry=isinstance(related['uid'], NewID))

    def parse_entry_review_status(self):
        if self.data.get('accept'):
            if self.user.user_role < USER_ROLES.Reviewer:
                raise InventoryPermissionError(
                    'You do not have the required permissions to change the review status!')
            self.entry['entry_review_status'] = 'accepted'
            self.entry['reviewed_by'] = UID(self.user.uid, facets={
                                            'timestamp': datetime.datetime.now(datetime.timezone.utc)})
            self.skip_keys.append('entry_review_status')
        elif self.data.get('entry_review_status'):
            if self.user.user_role < USER_ROLES.Reviewer:
                raise InventoryPermissionError(
                    'You do not have the required permissions to change the review status!')

    def parse_unique_name(self):
        if self.data.get('unique_name'):
            unique_name = self.data['unique_name'].strip().lower()
            if self.is_upsert:
                check = dgraph.get_uid('unique_name', unique_name)
                if check:
                    if check != str(self.entry_uid):
                        raise InventoryValidationError(
                            'Unique Name already taken!')
            self.entry['unique_name'] = unique_name
        else:
            name = slugify(self.data.get('name'), separator="_")
            query_string = f'''{{
                                field1 as var(func: eq(unique_name, "{name}"))
                                data1(func: uid(field1)) {{
                                        unique_name
                                        uid
                                }}
                                
                            }}'''

            result = dgraph.query(query_string)

            if len(result['data1']) == 0:
                self.entry['unique_name'] = name
            else:
                self.entry['unique_name'] = f'{name}_{secrets.token_urlsafe(4)}'

    def parse_wikidata(self):
        if not self.is_upsert:
            wikidata = get_wikidata(self.data.get('name'))
            if wikidata:
                for key, val in wikidata.items():
                    if val is None: continue
                    if key not in self.entry.keys():
                        self.entry[key] = val
                    elif key == 'other_names':
                        if 'other_names' not in self.entry.keys():
                            self.entry['other_names'] = []
                        self.entry[key] += val

    def generate_unique_name(self):
        name = slugify(self.data.get('name'), separator="_")
        query_string = f'''{{
                            field1 as var(func: eq(unique_name, "{name}"))
                            data1(func: uid(field1)) {{
                                    unique_name
                                    uid
                            }}
                            
                        }}'''

        result = dgraph.query(query_string)

        if len(result['data1']) == 0:
            self.entry['unique_name'] = name
        else:
            self.entry['unique_name'] = f'{name}_{secrets.token_urlsafe(4)}'


class OrganizationSanitizer(Sanitizer):

    def __init__(self, data, **kwargs):

        fields = Organization.predicates()

        super().__init__(data, fields=fields, **kwargs)

        if not self.is_upsert:
            self.entry['dgraph.type'].append('Organization')

        
def make_sanitizer(data: dict, dgraph_type, edit=False):

    if not isinstance(dgraph_type, str):
        dgraph_type = dgraph_type.__name__
    
    fields = Schema.get_predicates(dgraph_type)
    if Schema.get_reverse_predicates(dgraph_type):
        fields.update(Schema.get_reverse_predicates(dgraph_type))

    class S(Sanitizer):

        def __init__(self, d, dtype='Entry', *args, **kwargs):

            super().__init__(d, *args, **kwargs)

            if not self.is_upsert:
                self.entry['dgraph.type'].append(dtype)

    if edit:
        return S.edit(data, fields=fields, dtype=dgraph_type)
    return S(data, fields=fields, dtype=dgraph_type)
