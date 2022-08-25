from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.dgraph_types import (UID, MutualRelationship, NewID, Predicate, ReverseRelationship, Scalar,
                                        SingleRelationship, GeoScalar, Variable, make_nquad, dict_to_nquad)
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.add.external import (geocode, instagram,
                                         parse_meta, reverse_geocode, siterankdata, find_sitemaps, find_feeds,
                                         build_url, twitter, facebook, get_wikidata, telegram, vkontakte)
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.dgraph import User
from flaskinventory import dgraph
from flask import current_app
from werkzeug.datastructures import ImmutableMultiDict

from flaskinventory.main.model import Entry, Organization, Source
from flaskinventory.misc import get_ip
from flaskinventory.misc.utils import IMD2dict
from flask_login import current_user

# External Utilities

from slugify import slugify
import secrets
import re

import datetime
from dateutil import parser as dateparser


class Sanitizer:
    """ Base Class for validating data and generating mutation object
        Validates all predicates from dgraph type 'Entry'
        also keeps track of user & ip address.
        Relevant return attributes are upsert_query (string), set_nquads (string), delete_nquads (string)
    """

    upsert_query = None

    def __init__(self, data: dict, fields: dict = None, dgraph_type=Entry, entry_review_status=None, **kwargs):

        if isinstance(data, ImmutableMultiDict):
            data = IMD2dict(data)
        self.user = current_user
        self.user_ip = get_ip()
        self._validate_inputdata(data, self.user, self.user_ip)
        if not isinstance(dgraph_type, str):
            dgraph_type = dgraph_type.__name__
        self.dgraph_type = dgraph_type
        self.fields = fields or Schema.get_predicates(dgraph_type)
        if self.dgraph_type and fields is None:
            if Schema.get_reverse_predicates(dgraph_type):
                self.fields.update(Schema.get_reverse_predicates(dgraph_type))

        if self.user.user_role < USER_ROLES.Contributor:
            raise InventoryPermissionError

        self.data = data

        self.is_upsert = kwargs.get('is_upsert', False)
        self.skip_keys = kwargs.get('skip_keys', [])
        self.entry_review_status = entry_review_status
        self.overwrite = {}
        self.newsubunits = []

        self.entry = {}
        self.related_entries = []
        self.facets = {}
        self.entry_uid = None

        self.delete_nquads = None
        self.upsert_query = None
        self.set_nquads = None

        if not self.is_upsert:
            self.entry['dgraph.type'] = Schema.resolve_inheritance(dgraph_type)
        self._parse()
        self.process_related()
        if self.dgraph_type == 'Source':
            if not self.is_upsert or self.entry_review_status == 'draft':
                self.process_source()
        
        if self.dgraph_type == 'ResearchPaper':
            self.process_researchpaper()

        self._delete_nquads()
        self._set_nquads()

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
    def edit(cls, data: dict, fields=None, dgraph_type=Entry, **kwargs):
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
        
        entry_review_status = check.get('entry_review_status')

        edit_fields = fields or Schema.get_predicates(dgraph_type)
        if dgraph_type and fields is None:
            if Schema.get_reverse_predicates(dgraph_type):
                edit_fields.update(Schema.get_reverse_predicates(dgraph_type))

        if entry_review_status != 'draft':
            edit_fields = {key: field for key, field in edit_fields.items() if field.edit}

        if not isinstance(dgraph_type, str):
            dgraph_type = dgraph_type.__name__
            
        return cls(data, is_upsert=True, dgraph_type=dgraph_type, entry_review_status=entry_review_status, fields=edit_fields, **kwargs)

    def _set_nquads(self):
        nquads = dict_to_nquad(self.entry)
        for related in self.related_entries:
            nquads += dict_to_nquad(related)
        self.set_nquads = " \n".join(nquads)

    def _delete_nquads(self):
        if self.is_upsert:
            # for upserts, we first have to delete all list type predicates
            # otherwise, the user cannot remove relationships, but just add to them

            del_obj = []

            upsert_query = ''

            for key, val in self.overwrite.items():
                for predicate in list(set(val)):
                    del_obj.append({'uid': key, predicate: '*'})
                    try:
                        if isinstance(self.fields[predicate], (MutualRelationship, ReverseRelationship)):
                            var = Variable(predicate, 'uid')
                            upsert_query += f""" q_{predicate}(func: has(dgraph.type)) 
                                                    @filter(uid_in({predicate}, {key.query})) {{
                                                        {var.query}
                                                    }} """
                            del_obj.append({'uid': var, predicate: key})
                    except KeyError:
                        pass

            nquads = [" \n".join(dict_to_nquad(obj)) for obj in del_obj]
            self.delete_nquads = " \n".join(nquads)
            if upsert_query != '':
                self.upsert_query = upsert_query
            else:
                self.upsert_query = None 
        else:
            self.delete_nquads = None

    @staticmethod
    def _check_entry(uid):
        query = f'''query check_entry($value: string)
                    {{ q(func: uid($value)) @filter(has(dgraph.type))'''
        query += "{ unique_name dgraph.type entry_review_status entry_added { uid } } }"
        data = dgraph.query(query, variables={'$value': uid})

        if len(data['q']) == 0:
            return False

        return data['q'][0]

    def _add_entry_meta(self, entry, newentry=False):
        # verify that dgraph.type is not added to self if the entry already exists
        if newentry:
            if entry.get('dgraph.type'):
                if type(entry['dgraph.type']) != list:
                    entry['dgraph.type'] = Schema.resolve_inheritance(entry['dgraph.type'])
                elif isinstance(entry['dgraph.type'], list):
                    dtypes = []
                    for dt in  entry['dgraph.type']:
                        dtypes += Schema.resolve_inheritance(dt)
                    entry['dgraph.type'] = list(set(dtypes))
            else:
                entry['dgraph.type'] = ["Entry"]

            entry['unique_name'] = self.generate_unique_name(entry)

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
        # can only update on facet per mutation (no list facets)
        for key in self.data:
            if '|' in key:
                predicate, facet = key.split('|')
                if predicate in self.facets:
                    self.facets[predicate].update({facet: self.data[key]})
                else:
                    self.facets[predicate] = {facet: self.data[key]}
            
            # for list predicates, we track facets via the value
            if '@' in key:
                val, facet = key.split('@')
                self.facets[val] = {facet: self.data[key]}

    def _postprocess_list_facets(self):
        for _, ll in self.entry.items():
            if isinstance(ll, list):
                for val in ll:
                    if isinstance(val, Scalar):
                        if str(val) in self.facets.keys():
                            val.update_facets(self.facets[str(val)])
                

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
                print(facets)
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
                try:
                    self.entry[key] += validated
                except TypeError:
                    validated.append(self.entry[key])
                    self.entry[key] = validated
            elif type(validated) == set and key in self.entry.keys():
                self.entry[key] = set.union(validated, self.entry[key])
            else:
                self.entry[key] = validated

        if self.is_upsert:
            self.entry = self._add_entry_meta(self.entry)
            self.overwrite[self.entry_uid] = [item.predicate for k, item in self.fields.items() if item.overwrite and k in self.data.keys()]
        else:
            self.entry = self._add_entry_meta(self.entry, newentry=True)
            self.entry['unique_name'] = self.generate_unique_name(self.entry)

        self._postprocess_list_facets()

    def process_related(self):
        for related in self.related_entries:
            related = self._add_entry_meta(related, newentry=isinstance(related['uid'], NewID))
            if isinstance(related['uid'], NewID) and 'name' not in related.keys():
                related['name'] = str(related['uid']).replace('_:', '').replace('_', ' ').title()
            

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
            if self.entry_review_status == 'draft' and self.data['entry_review_status'] == 'pending':
                self.entry['entry_review_status'] = 'pending'
            elif self.data['entry_review_status'] == 'pending':
                self.entry_review_status == 'pending'
                self.entry['entry_review_status'] = 'pending'
            elif self.user.user_role >= USER_ROLES.Reviewer:
                validated = self.fields.get('entry_review_status').validate(self.data.get('entry_review_status'))
                self.entry['entry_review_status'] = validated
            else:
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
        elif not self.is_upsert:
            if self.dgraph_type == 'ResearchPaper':
                name = self.data.get('doi') or self.data.get('arxiv')
                if name is None:
                    name = slugify(self.data.get('title'), separator="_")
            else:
                name = slugify(self.data.get('name'), separator="_")

            query_string = f''' query quicksearch($value: string)
                                {{
                                data1(func: eq(unique_name, $value)) {{
                                        unique_name
                                        uid
                                }}
                                
                            }}'''

            result = dgraph.query(query_string, variables={'$value': name})

            if len(result['data1']) == 0:
                self.entry['unique_name'] = name
            else:
                self.entry['unique_name'] = f'{name}_{secrets.token_urlsafe(4)}'

    def parse_wikidata(self):
        predicates = Schema.get_predicates(self.dgraph_type)
        if not self.is_upsert:
            wikidata = get_wikidata(self.data.get('name'))
            if wikidata:
                for key, val in wikidata.items():
                    if val is None: continue
                    if key not in predicates.keys():
                        continue
                    if key not in self.entry.keys():
                        self.entry[key] = val
                    elif key == 'other_names':
                        if 'other_names' not in self.entry.keys():
                            self.entry['other_names'] = []
                        self.entry[key] += val

    def generate_unique_name(self, entry: dict):
        try:
            unique_name = slugify(str(entry['name']), separator="_")
        except KeyError:
            current_app.logger.debug(f'<{entry["uid"]}> No key "name" in dict. Autoassigning')
            unique_name = slugify(str(entry['uid']), separator="_")
            if hasattr(entry['uid'], 'original_value'):
                entry['name'] = entry['uid'].original_value        
        if dgraph.get_uid('unique_name', unique_name):
            unique_name += f'_{secrets.token_urlsafe(4)}'

        return unique_name

    def process_researchpaper(self):
        """
            Special steps for papers
            Generate a name based on author and title
            assign unique name based on DOI or arXiv
        """
        if isinstance(self.entry['authors'], list) and len(self.entry['authors']) > 1:
            author = f"{self.entry['authors'][0]} et al."
        elif isinstance(self.entry['authors'], list) and len(self.entry['authors']) == 1:
            author = f"{self.entry['authors'][0]}"
        else:
            author = f"{self.entry['authors']}"[:32]
        
        title = re.match(r".*?[\?:\.!]", str(self.entry['title']))[0]
        title = title.replace(':', '')

        year = self.entry['published_date'].year

        self.entry['name'] = f'{author} ({year}): {title}'

        if self.data.get('arxiv'):
            self.entry['unique_name'] = self.data['arxiv'].strip()
        if self.data.get('doi'):
            self.entry['unique_name'] = self.data['doi'].strip()


    def process_source(self):
        """
            Special processing step for new Sources
            We grab some additional data from various APIs
            And also make sure that _new_ related sources inherit fields
        """

        try:
            channel = dgraph.get_unique_name(self.entry['channel'].query)
        except KeyError:
            channel = dgraph.get_unique_name(self.data['channel'])

        if channel == 'website':
            self.resolve_website()
            self.fetch_siterankdata()
            self.fetch_feeds()
        elif channel == 'instagram':
            self.fetch_instagram()
        elif channel == 'twitter':
            self.fetch_twitter()
        elif channel == 'vkontakte':
            self.fetch_vk()
        elif channel == 'telegram':
            self.fetch_telegram()
        elif channel == 'facebook':
            self.entry['channel_url'] = self.entry['name']
        
        try: 
            country_uid = self.entry['country'][0]
        except TypeError:
            country_uid = self.entry['country']
            
        self.entry['unique_name'] = self.source_unique_name(self.entry['name'], channel=channel, country_uid=country_uid)

        # inherit from main source
        for source in self.related_entries:
            if isinstance(source['uid'], NewID):
                if 'Source' in source['dgraph.type']:
                    rel_channel = self.data.get('newsource_' + source['name'])
                    if rel_channel:
                        if dgraph.get_dgraphtype(rel_channel) == 'Channel':
                            source['channel'] = UID(rel_channel)
                    else:
                        raise InventoryValidationError(f'No channel provided for related source {source["name"]}! Please indicate channel')
                    source['entry_review_status'] = 'draft'
                    source['unique_name'] = secrets.token_urlsafe(8)
                    source['publication_kind'] = self.entry.get('publication_kind')
                    source['special_interest'] = self.entry.get('special_interest')
                    source['topical_focus'] = self.entry.get('topical_focus')
                    source['geographic_scope'] = self.entry.get('geographic_scope')
                    source['country'] = self.entry.get('country')
                    source['geographic_scope_subunit'] = self.entry.get('geographic_scope_subunit')
                    source['languages'] = self.entry.get('languages')
                    source['party_affiliated'] = self.entry.get('party_affiliated')                   
                    

    @staticmethod
    def source_unique_name(name, channel=None, country=None, country_uid=None):
        name = slugify(str(name), separator="_")
        channel = slugify(str(channel), separator="_")
        if country_uid:
            country = dgraph.query(
                f'''{{ q(func: uid({country_uid.query})) {{ unique_name }} }}''')
            country = country['q'][0]['unique_name']

        country = slugify(country, separator="_")
        query_string = f'''{{
                            field1 as var(func: eq(unique_name, "{name}"))
                            field2 as var(func: eq(unique_name, "{name}_{channel}"))
                            field3 as var(func: eq(unique_name, "{name}_{country}_{channel}"))
                        
                            data1(func: uid(field1)) {{
                                    unique_name
                                    uid
                            }}
                        
                            data2(func: uid(field2)) {{
                                unique_name
                                uid
                            }}

                            data3(func: uid(field3)) {{
                                unique_name
                                uid
                            }}
                            
                        }}'''

        result = dgraph.query(query_string)

        if len(result['data1']) == 0:
            return f'{name}'
        elif len(result['data2']) == 0:
            return f'{name}_{channel}'
        elif len(result['data3']) == 0:
            return f'{name}_{country}_{channel}'
        else:
            return f'{name}_{country}_{channel}_{secrets.token_urlsafe(4)}'


    def resolve_website(self):
        # first check if website exists
        entry_name = str(self.entry['name'])
        try:
            names, urls = parse_meta(entry_name)
        except:
            raise InventoryValidationError(
                f"Could not resolve website! URL provided does not exist: {self.data.get('name')}")

        if urls == False:
            raise InventoryValidationError(
                f"Could not resolve website! URL provided does not exist: {self.data.get('name')}")

        # clean up the display name of the website
        entry_name = entry_name.replace(
            'http://', '').replace('https://', '').lower()
        
        if entry_name.endswith('/'):
            entry_name = entry_name[:-1]

        # append automatically retrieved names to other_names
        if len(names) > 0:
            if 'other_names' not in self.entry.keys():
                self.entry['other_names'] = []
            for name in names:
                if name.strip() == '':
                    continue
                if name not in self.entry['other_names']:
                    self.entry['other_names'].append(name.strip())

        if len(urls) > 0:
            if 'other_names' not in self.entry.keys():
                self.entry['other_names'] = []
            for url in urls:
                if url.strip() == '':
                    continue
                if url not in self.entry['other_names']:
                    self.entry['other_names'].append(url.strip())
        
        self.entry['name'] = Scalar(entry_name)
        self.entry['channel_url'] = build_url(
            self.data['name'])

    def fetch_siterankdata(self):
        try:
            daily_visitors = siterankdata(self.entry['name'])
        except Exception as e:
            current_app.logger.warning(f'Could not fetch siterankdata for {self.entry["name"]}! Exception: {e}')
            daily_visitors = None

        if daily_visitors:
            self.entry['audience_size'] = Scalar(datetime.date.today(), facets={
                'count': daily_visitors,
                'unit': "daily visitors",
                'data_from': f"https://siterankdata.com/{str(self.entry['name']).replace('www.', '')}"})

    def fetch_feeds(self):
        self.entry['channel_feeds'] = []
        sitemaps = find_sitemaps(self.entry['name'])
        if len(sitemaps) > 0:
            for sitemap in sitemaps:
                self.entry['channel_feeds'].append(
                    Scalar(sitemap, facets={'kind': 'sitemap'}))

        feeds = find_feeds(self.entry['name'])

        if len(feeds) > 0:
            for feed in feeds:
                self.entry['channel_feeds'].append(
                    Scalar(feed, facets={'kind': 'rss'}))

    def fetch_instagram(self):
        profile = instagram(self.data['name'].replace('@', ''))
        if profile:
            self.entry['name'] = self.data[
                'name'].lower().replace('@', '')
            self.entry['channel_url'] = self.data[
                'name'].lower().replace('@', '')
        else:
            raise InventoryValidationError(
                f"Instagram profile not found: {self.data['name']}")

        if profile.get('fullname'):
            try:
                self.entry['other_names'].append(profile['fullname'])
            except KeyError:
                self.entry['other_names'] = [profile['fullname']]
        if profile.get('followers'):
            facets = {'count': int(
                profile['followers']),
                'unit': 'followes'}
            self.entry['audience_size'] = Scalar(
                str(datetime.date.today()), facets=facets)
        self.entry['verified_account'] = profile['verified']

    def fetch_twitter(self):
        self.entry['channel_url'] = self.data['name'].replace('@', '')
        try:
            profile = twitter(self.data['name'].replace('@', ''))
        except Exception as e:
            raise InventoryValidationError(
                f"Twitter profile not found: {self.data['name']}. {e}")

        self.entry['name'] = self.data[
            'name'].lower().replace('@', '')

        if profile.get('fullname'):
            try:
                self.entry['other_names'].append(profile['fullname'])
            except KeyError:
                self.entry['other_names'] = [profile['fullname']]
        if profile.get('followers'):
            facets = {'count': int(
                profile['followers']),
                'unit': 'followers'}
            self.entry['audience_size'] = Scalar(
                str(datetime.date.today()), facets=facets)
        if profile.get('joined'):
            self.entry['founded'] = profile.get('joined').isoformat()
        self.entry['verified_account'] = profile.get('verified')

    def fetch_vk(self):
        self.entry['channel_url'] = self.data[
            'name'].replace('@', '')
        try:
            profile = vkontakte(self.data['name'].replace('@', ''))
        except Exception as e:
            raise InventoryValidationError(
                f"VKontakte profile not found: {self.data['name']}. {e}")

        self.entry['name'] = self.data[
            'name'].lower().replace('@', '')

        if profile.get('fullname'):
            self.entry['other_names'].append(profile['fullname'])
        if profile.get('followers'):
            facets = {'count': int(
                profile['followers']),
                'unit': 'followers'}
            self.entry['audience_size'] = Scalar(
                str(datetime.date.today()), facets=facets)
        self.entry['verified_account'] = profile.get('verified')
        if profile.get('description'):
            self.entry['description'] = profile.get('description')

    def fetch_telegram(self):
        self.entry['channel_url'] = self.data[
            'name'].replace('@', '')
        try:
            profile = telegram(self.data['name'].replace('@', ''))
        except Exception as e:
            current_app.logger.error(
                f'Telegram could not be resolved. username: {self.data["name"]}. Exception: {e}')
            raise InventoryValidationError(
                f"""Telegram user or channel not found: {self.data['name']}. 
                    Please check whether you typed the username correctly. 
                    If the issue persists, please contact us and we will look into this issue.""")

        if profile == False:
            raise InventoryValidationError(
                f"""Telegram user or channel not found: {self.data['name']}. 
                    Please check whether you typed the username correctly. 
                    If the issue persists, please contact us and we will look into this issue.""")

        self.entry['name'] = self.data[
            'name'].lower().replace('@', '')

        if profile.get('fullname'):
            try:
                self.entry['other_names'].append(profile['fullname'])
            except KeyError:
                self.entry['other_names'] = [profile['fullname']]
        if profile.get('followers'):
            facets = {'count': int(
                profile['followers']),
                'unit': 'followers'}
            self.entry['audience_size'] = Scalar(
                str(datetime.date.today()), facets=facets)
        self.entry['verified_account'] = profile.get('verified', False)
        if profile.get('telegram_id'):
            self.entry['channel_url'] = profile.get('telegram_id')
        if profile.get('joined'):
            self.entry['founded'] = profile.get('joined')



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
