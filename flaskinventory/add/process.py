from flaskinventory.add.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.add.external import (geocode, instagram,
                                             parse_meta, siterankdata, find_sitemaps, find_feeds,
                                             build_url, twitter, facebook)
from flaskinventory import dgraph
from flask import current_app
from slugify import slugify
import secrets

import datetime


class EntryProcessor():
    """ Class for validating data and generating mutation object
        takes dict (from json) as input and validates all entries accordingly
        also keeps track of user & ip address
        relevant return attribute is 'mutation' (list)
    """

    payment_model = ['free', 'soft paywall', 'subscription', 'none']
    contains_ads = ['yes', 'no', 'non subscribers', 'none']
    ownership_kind = ['public ownership',
                      'private ownership', 'unknown', 'none']
    special_interest = ['yes', 'no']
    publication_cycle = ['continuous', 'daily', 'multiple times per week',
                         'weekly', 'twice a month', 'monthly', 'none']
    geographic_scope = ['multinational', 'national', 'subnational', 'none']
    transcript_kind = ['tv', 'radio', 'podcast', 'none']
    channel_comments = ['no comments', 'user comments with registration',
                        'user comments without registration', 'none']

    def __init__(self, json, user, ip):
        self.json = json
        self.user = user
        self.user_ip = ip
        self.new_source = {'uid': '_:newsource',
                           'dgraph.type': 'Source',
                           'channel': dict(),
                           'other_names': [],
                           'related': []}
        self.mutation = []

        if self.json.get('channel') == 'print':
            self.process_print()
        elif self.json.get('channel') == 'website':
            self.process_website()
        elif self.json.get('channel') == 'instagram':
            self.process_instagram()
        elif self.json.get('channel') == 'transcript':
            self.process_transcript()
        elif self.json.get('channel') == 'twitter':
            self.process_twitter()
        elif self.json.get('channel') == 'facebook':
            self.process_facebook()
        else:
            raise NotImplementedError('Cannot process submitted news source.')

    def add_entry_meta(self, entry, entry_status="pending"):
        if self.user.is_authenticated:
            entry['entry_added'] = {'uid': self.user.uid}
        entry['entry_added|timestamp'] = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        entry['entry_added|ip'] = self.user_ip
        entry['entry_review_status'] = entry_status

        return entry

    def process_print(self):

        # general info
        self.parse_name()
        self.parse_channel()
        self.parse_other_names()
        self.parse_epaper()
        self.parse_founded()

        # economic
        self.parse_payment_model()
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()
        self.parse_audience_size()

        # access to data
        self.parse_archives()
        self.parse_datasets()

        # other information
        self.parse_entry_notes()
        self.parse_related()

        # generate unique name
        self.generate_unique_name()

        self.new_source = self.add_entry_meta(self.new_source)

        self.mutation.append(self.new_source)

    def process_transcript(self):
        self.parse_channel()
        self.parse_name()
        self.parse_channel_url()
        self.parse_transcriptkind()
        self.parse_other_names()
        self.parse_founded()

        # economic
        self.parse_payment_model()
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()

        # access to data
        self.parse_archives()
        self.parse_datasets()

        # other information
        self.parse_entry_notes()
        self.parse_related()

        self.generate_unique_name()

        self.new_source = self.add_entry_meta(self.new_source)

        self.mutation.append(self.new_source)

    def process_website(self):

        # general information
        self.parse_channel()
        self.resolve_website()  # check if website exists / parse url
        self.parse_other_names()
        self.parse_channel_comments()
        self.parse_founded()

        # economic
        self.parse_payment_model()
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()

        # get audience size from siterankdata.com
        self.fetch_siterankdata()

        # access to data
        self.parse_archives()
        self.parse_datasets()

        # other information
        self.parse_entry_notes()
        self.parse_related()

        # get feeds
        self.fetch_feeds()

        self.generate_unique_name()

        self.new_source = self.add_entry_meta(self.new_source)

        self.mutation.append(self.new_source)

    def process_instagram(self):

        # general info
        self.parse_channel()
        self.fetch_instagram()
        self.parse_other_names()
        self.parse_founded()

        # economic
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()

        # data access
        self.parse_archives()
        self.parse_datasets()

        # other
        self.parse_entry_notes()
        self.parse_related()

        self.generate_unique_name()
        self.new_source = self.add_entry_meta(self.new_source)
        self.mutation.append(self.new_source)

    def process_twitter(self):
        self.parse_channel()
        self.fetch_twitter()

        self.parse_other_names()

        # economic
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()

        # data access
        self.parse_archives()
        self.parse_datasets()

        # other
        self.parse_entry_notes()
        self.parse_related()

        self.generate_unique_name()
        self.new_source = self.add_entry_meta(self.new_source)
        self.mutation.append(self.new_source)

    def process_facebook(self):
        self.parse_channel()
        self.fetch_facebook()

        self.parse_other_names()
        self.parse_founded()

        # economic
        self.parse_contains_ads()
        self.parse_org()
        self.parse_person()

        # journalistic routines
        self.parse_publication_kind()
        self.parse_special_interest()
        self.parse_publication_cycle()

        # audience related
        self.parse_geographic_scope()
        self.parse_languages()

        # data access
        self.parse_archives()
        self.parse_datasets()

        # other
        self.parse_entry_notes()
        self.parse_related()

        self.generate_unique_name()
        self.new_source = self.add_entry_meta(self.new_source)
        self.mutation.append(self.new_source)

    def parse_name(self):
        if self.json.get('name'):
            self.new_source['name'] = self.json.get('name')
        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def parse_channel(self):
        try:
            if self.json.get('channel_uid').startswith('0x'):
                self.new_source['channel']['uid'] = self.json.get('channel_uid')
        except Exception as e:
            raise InventoryValidationError(
                f'Invalid data! uid of channel not defined: {e}')

    def parse_channel_url(self):
        if self.json.get('channel_url'):
            self.new_source['channel_url'] = self.json.get('channel_url')

    def parse_other_names(self):
        if self.json.get('other_names'):
            self.new_source['other_names'] += self.json.get(
                'other_names').split(',')

    def parse_epaper(self):
        if self.json.get('channel_epaper'):
            self.new_source['channel_epaper'] = self.json.get('channel_epaper')

    def resolve_website(self):
        if self.json.get('name'):

            urls, names = parse_meta(self.json.get('name'))
            if urls == False:
                raise InventoryValidationError(
                    f"Could not resolve website! URL provided does not exist: {self.json.get('name')}")

            self.new_source['name'] = self.json.get('name').replace(
                'http://', '').replace('https://', '').lower()
            if self.new_source['name'].endswith('/'):
                self.new_source['name'] = self.new_source['name'][:-1]

            if len(names) > 0:
                self.new_source['other_names'] += names
            if len(urls) > 0:
                self.new_source['other_names'] += urls
            self.new_source['channel_url'] = build_url(
                self.json.get('name'))

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def parse_channel_comments(self):
        if self.json.get('channel_comments'):
            if self.json.get('channel_comments').lower() in self.channel_comments:
                self.new_source['channel_comments'] = self.json.get(
                    'channel_comments').lower()
            else:
                raise InventoryValidationError(
                    f"Invalid data! Provided value for 'channel_comments' does not match: {self.json.get('channel_comments')}")
        else:
            self.new_source['channel_comments'] = 'none'

    def parse_founded(self):
        if self.json.get('founded'):
            try:
                founded = int(self.json.get('founded'))
                if founded < 1700:
                    raise InventoryValidationError(
                        f'Invalid data! "founded" too small: {founded}')
                if founded > 2100:
                    raise InventoryValidationError(
                        f'Invalid data! "founded" too large: {founded}')
                self.new_source['founded'] = str(founded)
            except ValueError:
                raise InventoryValidationError(
                    f'Invalid Data! Cannot parse value for "founded" to int: {self.json.get("founded")}')

    def parse_payment_model(self):
        if self.json.get('payment_model'):
            if self.json.get('payment_model').lower() in self.payment_model:
                self.new_source['payment_model'] = self.json.get(
                    'payment_model').lower()
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "payment_model": {self.json.get("payment_model")}')

    def parse_contains_ads(self):
        if self.json.get('contains_ads'):
            if self.json.get('contains_ads').lower() in self.contains_ads:
                self.new_source['contains_ads'] = self.json.get(
                    'contains_ads').lower()
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "contains_ads": {self.json.get("contains_ads")}')

    def parse_publication_kind(self):
        if self.json.get('publication_kind'):
            if type(self.json.get('publication_kind')) == list:
                self.new_source['publication_kind'] = [item.lower()
                                                       for item in self.json.get('publication_kind')]
            else:
                self.new_source['publication_kind'] = self.json.get(
                    'publication_kind').lower()

    def parse_special_interest(self):
        if self.json.get('special_interest'):
            if self.json.get('special_interest').lower() in self.special_interest:
                if self.json.get('special_interest').lower() == 'yes':
                    self.new_source['special_interest'] = True
                else:
                    self.new_source['special_interest'] = False
                if self.json.get('special_interest').lower() == 'yes':
                    if self.json.get('topical_focus'):
                        if type(self.json.get('topical_focus')) == list:
                            self.new_source['topical_focus'] = [item.lower()
                                                                for item in self.json.get('topical_focus')]
                        else:
                            self.new_source['topical_focus'] = self.json.get(
                                'topical_focus').lower()
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "special_interest": {self.json.get("special_interest")}')

    def parse_publication_cycle(self):
        if self.json.get('publication_cycle'):
            if self.json.get('publication_cycle').lower() in self.publication_cycle:
                self.new_source['publication_cycle'] = self.json.get(
                    'publication_cycle').lower()
                if self.new_source['publication_cycle'] in ["multiple times per week", "weekly"]:
                    days_list = []
                    for item in self.json.keys():
                        if item.startswith('publication_cycle_weekday_'):
                            if self.json[item].lower() == 'yes':
                                if 'none' in item:
                                    days_list = []
                                    break
                                days_list.append(
                                    int(item.replace('publication_cycle_weekday_', '')))
                    self.new_source["publication_cycle_weekday"] = days_list
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "publication_cycle": {self.json.get("publication_cycle")}')

    def parse_geographic_scope(self):
        if self.json.get('geographic_scope'):
            if self.json.get('geographic_scope').lower() in self.geographic_scope:
                self.new_source['geographic_scope'] = self.json.get(
                    'geographic_scope').lower()
                if self.new_source['geographic_scope'] == 'multinational':
                    if self.json.get('geographic_scope_multiple'):
                        if self.json.get('geographic_scope_countries'):
                            self.new_source['geographic_scope_countries'] = []
                            for country in self.json.get('geographic_scope_countries').split(','):
                                if country.startswith('0x'):
                                    self.new_source['geographic_scope_countries'].append(
                                        {'uid': country})
                                else:
                                    # discard other data
                                    continue
                        if self.json.get('geographic_scope_subunits'):
                            self.new_source['geographic_scope_subunit'] = []
                            for subunit in self.json.get('geographic_scope_subunits').split(','):
                                if subunit == '':
                                    continue
                                elif subunit.startswith('0x'):
                                    self.new_source['geographic_scope_subunit'].append(
                                        {'uid': subunit})
                                else:
                                    geo_query = self.resolve_subunit(subunit)
                                    if geo_query:
                                        self.new_source['geographic_scope_subunit'].append(
                                            geo_query)

                elif self.new_source['geographic_scope'] == 'national':
                    if self.json.get('geographic_scope_single'):
                        if self.json.get('geographic_scope_single').startswith('0x'):
                            self.new_source['geographic_scope_countries'] = [
                                {'uid': self.json.get('geographic_scope_single')}]
                        else:
                            raise InventoryValidationError(
                                f'Invalid Data! "geographic_scope_single" not uid: {self.json.get("geographic_scope_single")}')
                elif self.new_source['geographic_scope'] == 'subnational':
                    if self.json.get('geographic_scope_single'):
                        if self.json.get('geographic_scope_single').startswith('0x'):
                            self.new_source['geographic_scope_countries'] = [
                                {'uid': self.json.get('geographic_scope_single')}]
                        else:
                            raise InventoryValidationError(
                                f'Invalid Data! "geographic_scope_single" not uid: {self.json.get("geographic_scope_single")}')
                    else:
                        raise InventoryValidationError(
                            'Invalid Data! need to specify at least one country!')
                    self.new_source['geographic_scope_subunit'] = self.parse_subunit(
                        self.json)
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "geographic_scope": {self.json.get("geographic_scope")}')
        else:
            raise InventoryValidationError(
                'Invalid data! "geographic_scope" is required')

    def parse_languages(self):
        if self.json.get('languages'):
            if type(self.json.get('languages')) == list:
                self.new_source['languages'] = [item.lower() for item in self.json.get(
                    'languages') if item.lower() in icu_codes.keys()]
            else:
                if self.json.get('languages').lower() in icu_codes.keys():
                    self.new_source['languages'] = [
                        self.json.get('languages').lower()]

    def parse_audience_size(self):
        if self.json.get('audience_size_subscribers'):
            self.new_source['audience_size|subscribers'] = int(
                self.json.get('audience_size_subscribers'))
            if self.json.get('audience_size_year'):
                self.new_source['audience_size'] = str(
                    int(self.json.get('audience_size_year')))
            else:
                self.new_source['audience_size'] = str(datetime.date.today())
            if self.json.get('audience_size_datafrom'):
                self.new_source['audience_size|datafrom'] = self.json.get(
                    'audience_size_datafrom')
            else:
                self.new_source['audience_size|datafrom'] = "unknown"

    def fetch_siterankdata(self):
        daily_visitors = siterankdata(self.new_source['name'])

        if daily_visitors:
            self.new_source['audience_size'] = str(datetime.date.today())
            self.new_source['audience_size|daily_visitors'] = daily_visitors
            self.new_source[
                'audience_size|datafrom'] = f"https://siterankdata.com/{self.new_source['name'].replace('www.', '')}"

    def source_unique_name(self, name, channel=None, channel_uid=None, country=None, country_uid=None):
        name = slugify(name, separator="_")
        channel = slugify(channel, separator="_")
        if country_uid:
            country = dgraph.query(
                f'''{{ q(func: uid({country_uid})) {{ unique_name }} }}''')
            country = country['q'][0]['unique_name']

        if channel_uid:
            channel = dgraph.query(
                f'''{{ q(func: uid({channel_uid})) {{ unique_name }} }}''')
            channel = country['q'][0]['unique_name']

        country = slugify(country, separator="_")
        query_string = f'''{{
                            field1 as var(func: eq(unique_name, "{name}_{channel}"))
                            field2 as var(func: eq(unique_name, "{name}_{country}_{channel}"))
                        
                            data1(func: uid(field1)) {{
                                    unique_name
                                    uid
                            }}
                        
                            data2(func: uid(field2)) {{
                                unique_name
                                uid
                            }}
                            
                        }}'''

        result = dgraph.query(query_string)

        if len(result['data1']) == 0:
            return f'{name}_{channel}'
        elif len(result['data2']) == 0:
            return f'{name}_{country}_{channel}'
        else:
            return f'{name}_{country}_{channel}_{secrets.token_urlsafe(4)}'

    def generate_unique_name(self):
        if self.new_source.get('geographic_scope_subunit'):
            current_app.logger.debug(
                self.new_source['geographic_scope_subunit'])
            if self.new_source['geographic_scope_subunit'][0]['uid'].startswith('0x'):
                self.new_source["unique_name"] = self.source_unique_name(
                    self.json['name'], channel=self.json['channel'], country_uid=self.new_source['geographic_scope_subunit'][0]['uid'])
            else:
                self.new_source["unique_name"] = self.source_unique_name(
                    self.json['name'], channel=self.json['channel'], country=self.new_source['geographic_scope_subunit'][0]['name'])

        elif 'uid' in self.new_source['geographic_scope_countries'][0].keys():
            self.new_source["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country_uid=self.new_source['geographic_scope_countries'][0]['uid'])
        else:
            self.new_source["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country="unknown")

    def parse_org(self):
        orgs = []
        if self.json.get('publishes_org'):
            if type(self.json.get('publishes_org')) != list:
                org_list = [self.json.get('publishes_org')]
            else:
                org_list = self.json.get('publishes_org')

            for item in org_list:
                org = {'publishes': [{'uid': "_:newsource"}],
                       'is_person': False}
                if item.startswith('0x'):
                    org['uid'] = item

                else:
                    org = self.add_entry_meta(org)
                    org['name'] = item
                    org['dgraph.type'] = "Organization"
                    unique_name = slugify(item, separator="_")
                    if dgraph.get_uid('unique_name', unique_name):
                        unique_name += secrets.token_urlsafe(3)
                    org['unique_name'] = unique_name
                    if self.json.get('ownership_kind'):
                        if self.json.get('ownership_kind').lower() in self.ownership_kind:
                            org["ownership_kind"] = self.json.get(
                                'ownership_kind').lower()
                        else:
                            raise InventoryValidationError(
                                f'Invalid data! Unknown value in "ownership_kind": {self.json.get("ownership_kind")}')
                orgs.append(org)
        if len(orgs) > 0:
            self.mutation += orgs

    def parse_person(self):
        persons = []
        if self.json.get('publishes_person'):
            if type(self.json.get('publishes_person')) != list:
                person_list = [self.json.get('publishes_person')]
            else:
                person_list = self.json.get('publishes_person')

            for item in person_list:
                pers = {'publishes': [{'uid': "_:newsource"}],
                        'is_person': True}
                if item.startswith('0x'):
                    pers['uid'] = item
                else:
                    pers = self.add_entry_meta(pers)
                    pers['name'] = item,
                    pers['dgraph.type'] = "Organization"
                    unique_name = slugify(item, separator="_")
                    if dgraph.get_uid('unique_name', unique_name):
                        unique_name += secrets.token_urlsafe(3)
                    pers['unique_name'] = unique_name
                # if self.json.get('ownership_kind'):
                #     if self.json.get('ownership_kind').lower() in self.ownership_kind:
                #         pers["ownership_kind"] = self.json.get(
                #             'ownership_kind').lower()
                #     else:
                #         raise InventoryValidationError(
                #             f'Invalid data! Unknown value in "ownership_kind": {self.json.get("ownership_kind")}')
                persons.append(pers)
        if len(persons) > 0:
            self.mutation += persons

    def parse_archives(self):
        archives = []
        if self.json.get('archive_sources_included'):
            if type(self.json.get('archive_sources_included')) != list:
                archive_list = [self.json.get('archive_sources_included')]
            else:
                archive_list = self.json.get('archive_sources_included')

            for item in archive_list:
                arch = {'sources_included': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    arch['uid'] = item

                else:
                    arch = self.add_entry_meta(arch)
                    arch['name'] = item,
                    arch['dgraph.type'] = "Archive"
                archives.append(arch)
        if len(archives) > 0:
            self.mutation += archives

    def parse_datasets(self):
        datasets = []
        if self.json.get('dataset_sources_included'):
            if type(self.json.get('dataset_sources_included')) != list:
                dataset_list = [self.json.get('dataset_sources_included')]
            else:
                dataset_list = self.json.get('dataset_sources_included')

            for item in dataset_list:
                dset = {'sources_included': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    dset['uid'] = item

                else:
                    dset = self.add_entry_meta(dset)
                    dset['name'] = item
                    dset['dgraph.type'] = "Dataset"
                datasets.append(dset)
        if len(datasets) > 0:
            self.mutation += datasets

    def parse_entry_notes(self):
        if self.json.get('entry_notes'):
            self.new_source['entry_notes'] = self.json.get('entry_notes')

    def parse_related(self):
        related = []
        if self.json.get('related_sources'):
            if type(self.json.get('related_sources')) != list:
                related_list = [self.json.get('related_sources')]
            else:
                related_list = self.json.get('related_sources')
            for item in related_list:
                rel_source = {'related': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    rel_source['uid'] = item
                    self.new_source['related'].append({'uid': item})
                else:
                    if self.json.get(f'newsource_{item}'):
                        channel_name, channel_uid = self.json.get(
                            'newsource_' + item).split(',')
                        rel_source = self.add_entry_meta(rel_source, entry_status="draft")
                        rel_source['name'] = item
                        rel_source['uid'] = f'_:{slugify(item, separator="_")}_{channel_name}'
                        rel_source['unique_name'] = secrets.token_urlsafe(8)
                        rel_source['dgraph.type'] = 'Source'
                        rel_source['channel'] = {
                            'uid': channel_uid}
                        self.new_source['related'].append(
                            {'uid': f'_:{slugify(item, separator="_")}_{channel_name}'})
                    else:
                        # just discard data if no channel is defined
                        continue
                related.append(rel_source)
            if len(related) > 0:
                self.mutation += related

    def resolve_geographic_name(self, query):
        geo_result = geocode(query)
        if geo_result:
            dql_string = f'''{{ q(func: eq(country_code, "{geo_result['address']['country_code']}")) @filter(type("Country")) {{ uid }} }}'''
            dql_result = dgraph.query(dql_string)
            try:
                country_uid = dql_result['q'][0]['uid']
            except Exception:
                raise InventoryValidationError(
                    f"Country not found in inventory: {geo_result['address']['country_code']}")
            geo_data = {'type': 'Point', 'coordinates': [
                float(geo_result.get('lon')), float(geo_result.get('lat'))]}

            other_names = list(
                {query, geo_result['namedetails']['name'], geo_result['namedetails']['name:en']})

            new_subunit = {'name': geo_result['namedetails']['name:en'],
                           'country': [{'uid': country_uid}],
                           'other_names': other_names,
                           'location_point': geo_data,
                           'country_code': geo_result['address']['country_code']}
            if geo_result.get('extratags'):
                if geo_result.get('extratags').get('wikidata'):
                    if geo_result.get('extratags').get('wikidata').lower().startswith('q'):
                        try:
                            new_subunit['wikidataID'] = int(geo_result.get(
                                'extratags').get('wikidata').lower().replace('q', ''))
                        except Exception as e:
                            current_app.logger.debug(
                                f'Could not parse wikidata ID in subunit: {e}')
                            pass

            return new_subunit
        else:
            return False

    def resolve_subunit(self, subunit):
        geo_query = self.resolve_geographic_name(subunit)
        if geo_query:
            geo_query = self.add_entry_meta(geo_query)
            geo_query['dgraph.type'] = 'Subunit'
            geo_query['unique_name'] = f"{slugify(subunit, separator='_')}_{geo_query['country_code']}"
            # prevent duplicates
            duplicate_check = dgraph.get_uid(
                'unique_name', geo_query['unique_name'])
            if duplicate_check:
                geo_query = {'uid': duplicate_check}
            else:
                geo_query['uid'] = f"_:{slugify(secrets.token_urlsafe(8))}"
            return geo_query
        else:
            raise InventoryValidationError(
                f'Invalid Data! Could not resolve geographic subunit {subunit}')

    def parse_subunit(self, data):
        subunits = []
        if data.get('geographic_scope_subunit'):
            if type(data.get('geographic_scope_subunit')) != list:
                subunit_list = [data.get('geographic_scope_subunit')]
            else:
                subunit_list = data.get('geographic_scope_subunit')

            for item in subunit_list:
                if item.startswith('0x'):
                    subunits.append({'uid': item})
                else:
                    geo_query = self.resolve_subunit(item)
                    if geo_query:
                        subunits.append(geo_query)
        return subunits

    def parse_transcriptkind(self):
        if self.json.get('transcript_kind'):
            if self.json.get('transcript_kind') in self.transcript_kind:
                self.new_source['transcript_kind'] = self.json.get(
                    'transcript_kind')
            else:
                raise InventoryValidationError(
                    f"Invalid Data! Unknown value for transcript_kind: {self.json.get('transcript_kind')}")
        else:
            raise InventoryValidationError(
                f"Missing Data! transcript_kind is required!")

    def fetch_feeds(self):
        self.new_source['channel_feeds'] = []
        self.new_source['channel_feeds|kind'] = dict()
        sitemaps = find_sitemaps(self.new_source['name'])
        if len(sitemaps) > 0:
            for i, sitemap in enumerate(sitemaps):
                self.new_source['channel_feeds'].append(sitemap)
                self.new_source['channel_feeds|kind'][i] = 'sitemap'

        feeds = find_feeds(self.new_source['name'])

        if len(feeds) > 0:
            for i, feed in enumerate(feeds, start=len(sitemaps)):
                self.new_source['channel_feeds'].append(feed)
                self.new_source['channel_feeds|kind'][i] = 'rss'

    def fetch_instagram(self):
        if self.json.get('name'):
            profile = instagram(self.json.get('name').replace('@', ''))
            if profile:
                self.new_source['name'] = self.json.get(
                    'name').lower().replace('@', '')
                self.new_source['channel_url'] = self.json.get(
                    'name').lower().replace('@', '')
            else:
                raise InventoryValidationError(
                    f"Instagram profile not found: {self.json.get('name')}")

            if profile.get('fullname'):
                self.new_source['other_names'].append(profile['fullname'])
            if profile.get('followers'):
                self.new_source['audience_size'] = str(datetime.date.today())
                self.new_source['audience_size|followers'] = int(
                    profile['followers'])
            if profile.get('verified'):
                self.new_source['verified_account'] = profile['verified']

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def fetch_twitter(self):
        if self.json.get('name'):
            self.new_source['channel_url'] = self.json.get(
                'name').replace('@', '')
            try:
                profile = twitter(self.json.get('name').replace('@', ''))
            except Exception as e:
                raise InventoryValidationError(
                    f"Twitter profile not found: {self.json.get('name')}. {e}")

            self.new_source['name'] = self.json.get(
                'name').lower().replace('@', '')

            if profile.get('fullname'):
                self.new_source['other_names'].append(profile['fullname'])
            if profile.get('followers'):
                self.new_source['audience_size'] = str(datetime.date.today())
                self.new_source['audience_size|followers'] = int(
                    profile['followers'])
            if profile.get('joined'):
                self.new_source['founded'] = profile.get('joined').isoformat()
            if profile.get('verified'):
                self.new_source['verified_account'] = profile.get('verified')

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def fetch_facebook(self):
        if self.json.get('name'):
            self.new_source['channel_url'] = self.json.get('name')
            self.new_source['name'] = self.json.get('name')
            # try:
            #     profile = facebook(self.json.get('name'))
            # except Exception as e:
            #     raise InventoryValidationError(
            #         f"Facebook profile not found: {self.json.get('name')}. {e}")

            # self.new_source['name'] = self.json.get('name').lower()

            # if profile.get('fullname'):
            #     self.new_source['other_names'].append(profile['fullname'])
            # if profile.get('followers'):
            #     self.new_source['audience_size'] = str(datetime.date.today())
            #     self.new_source['audience_size|followers'] = int(
            #         profile['followers'])
            # if profile.get('joined'):
            #     self.new_source['founded'] = profile.get('joined').isoformat()

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    # unique names of related & new sources are generated later (after reviewed)
