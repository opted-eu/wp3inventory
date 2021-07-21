from enum import unique
from hmac import new
from flaskinventory.records.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.records.external import geocode
from flaskinventory import dgraph
from slugify import slugify
import secrets

import datetime

class EntryProcessor():

    payment_model = ['free', 'soft paywall', 'subscription', 'none']
    contains_ads = ['yes', 'no', 'non subscribers', 'none']
    ownership_kind = ['public ownership', 'private ownership', 'unknown', 'none']
    special_interest = ['yes', 'no']
    publication_cycle = ['continuous', 'daily', 'multiple times per week',
                        'weekly', 'twice a month', 'monthly', 'none']
    geographic_scope = ['multinational', 'national', 'subnational', 'none']

    def __init__(self, json, user, ip):
        self.json = json
        self.user = user
        self.user_ip = ip

        if self.json.get('channel') == 'print':
            self.processed = self.process_print()

    def add_entry_meta(self, entry):
        if self.user.is_authenticated:
            entry['entry_added'] = {'uid': self.user.uid}
        entry['entry_added|timestamp'] = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        entry['entry_added|ip'] = self.user_ip
        entry['entry_review_status'] = "pending"

        return entry


    def process_print(self):

        new_print = {
            'uid': "_:newsource",
            'channel': {}
        }
    
        mutation = []

        if self.json.get('name'):
            new_print['name'] = self.json.get('name')
        else:
            raise InventoryValidationError('Invalid data! "name" not specified.')

        if self.json.get('channel_uid').startswith('0x'):
            new_print['channel']['uid'] = self.json.get('channel_uid')
        else:
            raise InventoryValidationError(
                'Invalid data! uid of channel not defined')

        if self.json.get('other_names'):
            new_print['other_names'] = self.json.get('other_names').split(',')

        if self.json.get('channel_epaper'):
            new_print['channel_epaper'] = self.json.get('channel_epaper')

        if self.json.get('founded'):
            try:
                founded = int(self.json.get('founded'))
                if founded < 1700:
                    raise InventoryValidationError(
                        'Invalid data! "founded" too small')
                if founded > 2100:
                    raise InventoryValidationError(
                        'Invalid data! "founded" too large')
                new_print['founded'] = founded
            except ValueError:
                raise InventoryValidationError(
                    'Invalid Data! Cannot parse "founded" to int.')

        if self.json.get('payment_model'):
            if self.json.get('payment_model').lower() in self.payment_model:
                new_print['payment_model'] = self.json.get('payment_model').lower()
            else:
                raise InventoryValidationError(
                    'Invalid data! Unknown value in "payment_model"')

        if self.json.get('contains_ads'):
            if self.json.get('contains_ads').lower() in self.contains_ads:
                new_print['contains_ads'] = self.json.get('contains_ads').lower()
            else:
                raise InventoryValidationError(
                    'Invalid data! Unknown value in "contains_ads"')

        # add relationship: publishes_org
        mutation += self.parse_org(self.json)
        mutation += self.parse_person(self.json)

        if self.json.get('publication_kind'):
            if type(self.json.get('publication_kind')) == list:
                new_print['publication_kind'] = [item.lower()
                                                for item in self.json.get('publication_kind')]
            else:
                new_print['publication_kind'] = self.json.get(
                    'publication_kind').lower()

        if self.json.get('special_interest'):
            if self.json.get('special_interest').lower() in self.special_interest:
                new_print['special_interest'] = self.json.get(
                    'special_interest').lower()
                if self.json.get('special_interest') == 'yes':
                    if self.json.get('topical_focus'):
                        if type(self.json.get('topical_focus')) == list:
                            new_print['topical_focus'] = [item.lower()
                                                        for item in self.json.get('topical_focus')]
                        else:
                            new_print['topical_focus'] = self.json.get(
                                'topical_focus').lower()
            else:
                raise InventoryValidationError(
                    'Invalid data! Unknown value in "special_interest"')

        if self.json.get('publication_cycle'):
            if self.json.get('publication_cycle').lower() in self.publication_cycle:
                new_print['publication_cycle'] = self.json.get(
                    'publication_cycle').lower()
                if new_print['publication_cycle'] in ["multiple times per week", "weekly"]:
                    days_list = []
                    for item in self.json.keys():
                        if item.startswith('publication_cycle_weekday_'):
                            if self.json[item].lower() == 'yes':
                                if 'none' in item:
                                    days_list = []
                                    break
                                days_list.append(
                                    int(item.replace('publication_cycle_weekday_', '')))
                    new_print["publication_cycle_weekday"] = days_list
            else:
                raise InventoryValidationError(
                    'Invalid data! Unknown value in "publication_cycle"')

        if self.json.get('geographic_scope'):
            if self.json.get('geographic_scope').lower() in self.geographic_scope:
                new_print['geographic_scope'] = self.json.get(
                    'geographic_scope').lower()
                if new_print['geographic_scope'] == 'multinational':
                    if self.json.get('geographic_scope_multiple'):
                        if self.json.get('geographic_scope_countries'):
                            new_print['geographic_scope_countries'] = []
                            for country in self.json.get('geographic_scope_countries').split(','):
                                if country.startswith('0x'):
                                    new_print['geographic_scope_countries'].append(
                                        {'uid': country})
                                else:
                                    continue
                        if self.json.get('geographic_scope_subunits'):
                            new_print['geographic_scope_subunit'] = []
                            for subunit in self.json.get('geographic_scope_subunits').split(','):
                                if subunit == '': continue
                                elif subunit.startswith('0x'):
                                    new_print['geographic_scope_subunit'].append(
                                        {'uid': subunit})
                                else:
                                    geo_query = self.resolve_subunit(subunit)
                                    if geo_query:
                                        new_print['geographic_scope_subunit'].append(geo_query)

                elif new_print['geographic_scope'] == 'national':
                    if self.json.get('geographic_scope_single'):
                        if self.json.get('geographic_scope_single').startswith('0x'):
                            new_print['geographic_scope_countries'] = [
                                {'uid': self.json.get('geographic_scope_single')}]
                        else:
                            raise InventoryValidationError(
                                'Invalid Data! "geographic_scope_single" not uid')
                elif new_print['geographic_scope'] == 'subnational':
                    if self.json.get('geographic_scope_single'):
                        if self.json.get('geographic_scope_single').startswith('0x'):
                            new_print['geographic_scope_countries'] = [
                                {'uid': self.json.get('geographic_scope_single')}]
                        else:
                            raise InventoryValidationError(
                                'Invalid Data! "geographic_scope_single" not uid')
                    else:
                        raise InventoryValidationError(
                            'Invalid Data! need to specify at least one country!')
                    new_print['geographic_scope_subunit'] = self.parse_subunit(self.json)
            else:
                raise InventoryValidationError(
                    'Invalid data! Unknown value in "geographic_scope"')
        else:
            raise InventoryValidationError(
                'Invalid data! "geographic_scope" is required')

        if self.json.get('languages'):
            if type(self.json.get('languages')) == list:
                new_print['languages'] = [item.lower() for item in self.json.get(
                    'languages') if item.lower() in icu_codes.keys()]
            else:
                if self.json.get('languages').lower() in icu_codes.keys():
                    new_print['languages'] = [self.json.get('languages').lower()]

        if self.json.get('audience_size_subscribers'):
            new_print['audience_size|subscribers'] = int(
                self.json.get('audience_size_subscribers'))
            if self.json.get('audience_size_year'):
                new_print['audience_size'] = str(
                    int(self.json.get('audience_size_year')))
            else:
                new_print['audience_size'] = str(datetime.date.today())
            if self.json.get('audience_size_datafrom'):
                new_print['audience_size|datafrom'] = self.json.get(
                    'audience_size_datafrom')
            else:
                new_print['audience_size|datafrom'] = "unknown"

        mutation += self.parse_archives(self.json)
        mutation += self.parse_datasets(self.json)

        if self.json.get('entry_notes'):
            new_print['entry_notes'] = self.json.get('entry_notes')

        mutation += self.parse_related(self.json)
        if self.json.get('related_sources'):
            if type(self.json.get('related_sources')) != list:
                related_list = [self.json.get('related_sources')]
            else:
                related_list = self.json.get('related_sources')
            new_print['related'] = []
            for item in related_list:
                if item.startswith('0x'):
                    new_print['related'].append({'uid': item})
                else:
                    related_src_channel, _ = self.json.get('newsource_' + item).split(',')
                    new_print['related'].append({'uid': f'_:{slugify(item, separator="_")}_{related_src_channel}'})

        # generate unique name

        if new_print.get('geographic_scope_subunit'):
            print(new_print['geographic_scope_subunit'])
            if 'uid' in new_print['geographic_scope_subunit'][0].keys():
                new_print["unique_name"] = self.source_unique_name(
                    self.json['name'], channel = self.json['channel'], country_uid=new_print['geographic_scope_subunit'][0]['uid'])
            else:
                new_print["unique_name"] = self.source_unique_name(
                    self.json['name'], channel = self.json['channel'], country=new_print['geographic_scope_subunit'][0]['name'])

        elif 'uid' in new_print['geographic_scope_countries'][0].keys():
            new_print["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country_uid=new_print['geographic_scope_countries'][0]['uid'])
        else:
            new_print["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country="unknown")

        new_print = self.add_entry_meta(new_print)

        mutation.append(new_print)

        return mutation


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


    def parse_org(self, data):
        orgs = []
        if data.get('publishes_org'):
            if type(data.get('publishes_org')) != list:
                org_list = [data.get('publishes_org')]
            else:
                org_list = data.get('publishes_org')

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
                if data.get('ownership_kind'):
                    if data.get('ownership_kind').lower() in self.ownership_kind:
                        org["ownership_kind"] = data.get('ownership_kind').lower()
                    else:
                        raise InventoryValidationError(
                            'Invalid data! Unknown value in "ownership_kind"')
                orgs.append(org)
        return orgs


    def parse_person(self, data):
        persons = []
        if data.get('publishes_person'):
            if type(data.get('publishes_person')) != list:
                person_list = [data.get('publishes_person')]
            else:
                person_list = data.get('publishes_person')

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
                if data.get('ownership_kind'):
                    if data.get('ownership_kind').lower() in self.ownership_kind:
                        pers["ownership_kind"] = data.get('ownership_kind').lower()
                    else:
                        raise InventoryValidationError(
                            'Invalid data! Unknown value in "ownership_kind"')
                persons.append(pers)
        return persons


    def parse_archives(self, data):
        archives = []
        if data.get('archive_sources_included'):
            if type(data.get('archive_sources_included')) != list:
                archive_list = [data.get('archive_sources_included')]
            else:
                archive_list = data.get('archive_sources_included')

            for item in archive_list:
                arch = {'sources_included': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    arch['uid'] = item

                else:
                    arch = self.add_entry_meta(arch)
                    arch['name'] = item,
                    arch['dgraph.type'] = "Archive"
                archives.append(arch)
        return archives


    def parse_datasets(self, data):
        datasets = []
        if data.get('dataset_sources_included'):
            if type(data.get('dataset_sources_included')) != list:
                dataset_list = [data.get('dataset_sources_included')]
            else:
                dataset_list = data.get('dataset_sources_included')

            for item in dataset_list:
                dset = {'sources_included': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    dset['uid'] = item

                else:
                    dset = self.add_entry_meta(dset)
                    dset['name'] = item
                    dset['dgraph.type'] = "Dataset"
                datasets.append(dset)
        return datasets


    def parse_related(self, data):
        related = []
        if data.get('related_sources'):
            if type(data.get('related_sources')) != list:
                related_list = [data.get('related_sources')]
            else:
                related_list = data.get('related_sources')
            for item in related_list:
                rel_source = {'related': [{'uid': '_:newsource'}]}
                if item.startswith('0x'):
                    rel_source['uid'] = item
                else:
                    if data.get(f'newsource_{item}'):
                        channel_name, channel_uid = data.get('newsource_' + item).split(',')
                        rel_source = self.add_entry_meta(rel_source)
                        rel_source['name'] = item
                        rel_source['uid'] = f'_:{slugify(item, separator="_")}_{channel_name}'
                        rel_source['unique_name'] = secrets.token_urlsafe(8)
                        rel_source['dgraph.type'] = 'Source'
                        rel_source['channel'] = {
                            'uid': channel_uid}
                    else:
                        # just discard data if no channel is defined
                        continue
                related.append(rel_source)

        return related


    def resolve_geographic_name(self, query):
        geo_result = geocode(query)
        if geo_result:
            dql_string = f'''{{ q(func: eq(country_code, "{geo_result['address']['country_code']}")) @filter(type("Country")) {{ uid }} }}'''
            dql_result = dgraph.query(dql_string)
            try:
                country_uid = dql_result['q'][0]['uid']
            except Exception:
                raise InventoryValidationError('Country not found in inventory!')
            geo_data = {'type': 'point', 'coordinates': [
                geo_result.get('lon'), geo_result.get('lat')]}
            
            other_names = list({query, geo_result['namedetails']['name'], geo_result['namedetails']['name:en']})

            return {'name': geo_result['namedetails']['name:en'], 
                        'country': [{'uid': country_uid}], 
                        'other_names': other_names, 
                        'location_point': geo_data, 
                        'country_code': geo_result['address']['country_code']}
        else:
            return False

    def resolve_subunit(self, subunit):
        geo_query = self.resolve_geographic_name(subunit)
        if geo_query:
            geo_query = self.add_entry_meta(geo_query)
            geo_query['dgraph.type'] = 'Subunit'
            geo_query['unique_name'] = f"{slugify(subunit, separator='_')}_{geo_query['country_code']}"
            return geo_query
        else:
            raise InventoryValidationError(f'Invalid Data! Could not resolve geographic subunit {subunit}')

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


    # unique names of related & new sources are generated later (after reviewed)
