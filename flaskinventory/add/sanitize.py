from flaskinventory.flaskdgraph import (UID, NewID, Predicate, Scalar,
                                        Geolocation, Variable, make_nquad, dict_to_nquad)
from flaskinventory.add.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.add.external import (geocode, instagram,
                                         parse_meta, reverse_geocode, siterankdata, find_sitemaps, find_feeds,
                                         build_url, twitter, facebook, get_wikidata, vkontakte)
from flaskinventory import dgraph
from flask import current_app
from slugify import slugify
import secrets

import datetime


class SourceSanitizer:
    """ Class for validating data and generating mutation object
        takes dict (from json) as input and validates all entries accordingly
        also keeps track of user & ip address.
        Relevant return attribute are upsert_query (string), set_nquads (string), delete_nquads (string)
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

    is_upsert = False
    upsert_query = None
    newsource = None
    set_nquads = None
    delete_nquads = None

    def __init__(self, json, user, ip):
        self.json = json
        self.user = user
        self.user_ip = ip
        self.uid = self.json.get('uid', '_:newsource')
        if self.uid.startswith('0x'):
            self.uid = UID(self.uid)
            self.is_upsert = True
            self.upsert_query = ''
        else:
            self.uid = NewID(self.uid)
        self.newsource = {'uid': self.uid,
                          'dgraph.type': "Source",
                          'geographic_scope_countries': [],
                          'other_names': []}

        self.newsubunits = []
        self.orgs = []
        self.archives = []
        self.related = []

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
        elif self.json.get('channel') == 'vkontakte':
            self.process_vk()
        else:
            raise NotImplementedError('Cannot process submitted news source.')

        if self.is_upsert:
            self.delete_nquads = self.make_delete_nquads()

        self.set_nquads = self.make_set_nquads()

    @staticmethod
    def enquote(string):
        return f'"{string.strip()}"'

    def make_delete_nquads(self):
        # for upserts, we first have to delete all list type predicates
        # otherwise, the user cannot remove relationships, but just add to them
        del_obj = []
        del_obj.append({
            'uid': self.newsource['uid'],
            'geographic_scope_subunit': '*'})

        del_obj.append({
            'uid': self.newsource['uid'],
            'geographic_scope_countries': '*'})

        # delete publication_kind, languages
        del_obj.append({
            'uid': self.newsource['uid'],
            'publication_kind': '*'})
        
        del_obj.append({
            'uid': self.newsource['uid'],
            'languages': '*'})

        # delete all "Organization" <publishes> "Upserted Source"
        orgs = Variable('orgs', 'uid')
        self.upsert_query += f""" q_organizations(func: type(Organization)) 
                            @filter(uid_in(publishes, {self.newsource['uid']})) 
                            {{ {orgs.query()} }} """
        del_obj.append({
            'uid': orgs,
            'publishes': self.newsource['uid']})

        # delete all "Archive" <includes> "Upserted Source"
        archives = Variable('archives', 'uid')
        self.upsert_query += f""" q_archives(func: type(Archive)) 
                            @filter(uid_in(sources_included, {self.newsource['uid']})) 
                            {{ {archives.query()} }} """
        del_obj.append({
            'uid': archives,
            'sources_included': self.newsource['uid']})

        # delete all "Dataset" <includes> "Upserted Source"
        datasets = Variable('datasets', 'uid')
        self.upsert_query += f""" q_datasets(func: type(Dataset)) 
                            @filter(uid_in(sources_included, {self.newsource['uid']})) 
                            {{ {datasets.query()} }} """
        del_obj.append({
            'uid': datasets,
            'sources_included': self.newsource['uid']})
        # delete all related
        related = Variable('related', 'uid')
        self.upsert_query += f""" q_related(func: type(Source)) 
                            @filter(uid_in(related, {self.newsource['uid']})) 
                            {{ {related.query()} }} """
        del_obj.append({
            'uid': related,
            'related': self.newsource['uid']
        })
        del_obj.append({
            'uid': self.newsource['uid'],
            'related': '*'
        })
        nquads = [" \n ".join(dict_to_nquad(obj)) for obj in del_obj]
        return " \n ".join(nquads)

    def make_set_nquads(self):
        nquads = dict_to_nquad(self.newsource)
        for subunit in self.newsubunits:
            nquads += dict_to_nquad(subunit)
        for org in self.orgs:
            nquads += dict_to_nquad(org)
        for archive in self.archives:
            nquads += dict_to_nquad(archive)
        for related in self.related:
            nquads += dict_to_nquad(related)
        return " \n ".join(nquads)

    def add_entry_meta(self, entry, entry_status="pending"):
        facets = {'timestamp': datetime.datetime.now(
            datetime.timezone.utc),
            'ip': self.user_ip}
        entry['entry_added'] = UID(self.user.uid, facets=facets)
        entry['entry_review_status'] = entry_status
        entry['creation_date'] = datetime.datetime.now(
            datetime.timezone.utc)

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

        self.newsource = self.add_entry_meta(self.newsource)

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

        self.newsource = self.add_entry_meta(self.newsource)

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

        self.newsource = self.add_entry_meta(self.newsource)

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
        self.newsource = self.add_entry_meta(self.newsource)

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
        self.newsource = self.add_entry_meta(self.newsource)

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
        self.newsource = self.add_entry_meta(self.newsource)

    def process_vk(self):
        self.parse_channel()
        self.fetch_vk()

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
        self.newsource = self.add_entry_meta(self.newsource)

    def parse_name(self):
        if self.json.get('name'):
            self.newsource['name'] = self.json.get('name')
        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def parse_channel(self):
        try:
            if self.json.get('channel_uid').startswith('0x'):
                self.newsource['channel'] = UID(self.json.get('channel_uid'))
            else:
                raise InventoryValidationError(
                    f'Invalid data! Only supports existing Channels with uid: {self.json.get("channel_uid")}')
        except Exception as e:
            raise InventoryValidationError(
                f'Invalid data! uid of channel not defined: {e}')

    def parse_channel_url(self):
        if self.json.get('channel_url'):
            self.newsource['channel_url'] = self.json.get('channel_url')

    def parse_other_names(self):
        if self.json.get('other_names'):
            if not self.newsource.get('other_names'):
                self.newsource['other_names'] = []

            self.newsource['other_names'] += [item for item in self.json.get(
                'other_names').split(',') if item.strip() != '']

    def parse_epaper(self):
        if self.json.get('channel_epaper'):
            self.newsource['channel_epaper'] = self.json.get('channel_epaper')

    def resolve_website(self):
        if self.json.get('name'):

            try:
                urls, names = parse_meta(self.json.get('name'))
            except:
                raise InventoryValidationError(
                    f"Could not resolve website! URL provided does not exist: {self.json.get('name')}")

            if urls == False:
                raise InventoryValidationError(
                    f"Could not resolve website! URL provided does not exist: {self.json.get('name')}")
                

            self.newsource['name'] = self.json.get('name').replace(
                'http://', '').replace('https://', '').lower()
            if self.newsource['name'].endswith('/'):
                self.newsource['name'] = self.newsource['name'][:-1]

            if len(names) > 0:
                for name in names:
                    if name.strip() == '':
                        continue
                    if name not in self.newsource['other_names']:
                        self.newsource['other_names'].append(name)

            if len(urls) > 0:
                for url in urls:
                    if url.strip() == '':
                        continue
                    if url not in self.newsource['other_names']:
                        self.newsource['other_names'].append(url)

            self.newsource['channel_url'] = build_url(
                self.json.get('name'))

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def parse_channel_comments(self):
        if self.json.get('channel_comments'):
            if self.json.get('channel_comments').lower() in self.channel_comments:
                self.newsource['channel_comments'] = self.json.get(
                    'channel_comments').lower()
            else:
                raise InventoryValidationError(
                    f"Invalid data! Provided value for 'channel_comments' does not match: {self.json.get('channel_comments')}")
        else:
            self.newsource['channel_comments'] = 'none'

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
                self.newsource['founded'] = str(founded)

            except ValueError:
                raise InventoryValidationError(
                    f'Invalid Data! Cannot parse value for "founded" to int: {self.json.get("founded")}')

    def parse_payment_model(self):
        if self.json.get('payment_model'):
            if self.json.get('payment_model').lower() in self.payment_model:
                self.newsource['payment_model'] = self.json.get(
                    'payment_model').lower()

            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "payment_model": {self.json.get("payment_model")}')

    def parse_contains_ads(self):
        if self.json.get('contains_ads'):
            if self.json.get('contains_ads').lower() in self.contains_ads:
                self.newsource['contains_ads'] = self.json.get(
                    'contains_ads').lower()
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "contains_ads": {self.json.get("contains_ads")}')

    def parse_publication_kind(self):
        if self.json.get('publication_kind'):
            self.newsource['publication_kind'] = []
            publication_kind = self.json.get('publication_kind')
            if type(publication_kind) == str:
                publication_kind = publication_kind.split(',')
            for item in publication_kind:
                if item.strip() == '':
                    continue
                self.newsource['publication_kind'].append(item.lower().strip())

    def parse_special_interest(self):
        if self.json.get('special_interest'):
            if self.json.get('special_interest').lower() in self.special_interest:
                if self.json.get('special_interest').lower() == 'yes':
                    self.newsource['special_interest'] = True

                else:
                    self.newsource['special_interest'] = False

                if self.newsource['special_interest']:
                    if self.json.get('topical_focus'):
                        topical_focus = self.json.get('topical_focus')
                        if type(topical_focus) == str:
                            topical_focus = topical_focus.split(',')
                        self.newsource['topical_focus'] = [
                            item.lower() for item in topical_focus if item.strip() != '']

            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "special_interest": {self.json.get("special_interest")}')

    def parse_publication_cycle(self):
        if self.json.get('publication_cycle'):
            if self.json.get('publication_cycle').lower() in self.publication_cycle:
                self.newsource['publication_cycle'] = self.json.get(
                    'publication_cycle').lower()
                if self.newsource['publication_cycle'] in ["multiple times per week", "weekly"]:
                    days_list = []
                    for item in self.json.keys():
                        if item.startswith('publication_cycle_weekday_'):
                            if self.json[item].lower() == 'yes':
                                if 'none' in item:
                                    days_list = []
                                    break
                                days_list.append(
                                    int(item.replace('publication_cycle_weekday_', '')))
                    self.newsource["publication_cycle_weekday"] = days_list
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "publication_cycle": {self.json.get("publication_cycle")}')

    def parse_geographic_scope(self):
        if self.json.get('geographic_scope'):
            if self.json.get('geographic_scope').lower() in self.geographic_scope:
                self.newsource['geographic_scope'] = self.json.get(
                    'geographic_scope').lower()

                if self.newsource['geographic_scope'] == 'multinational':
                    if self.json.get('geographic_scope_multiple'):
                        if self.json.get('geographic_scope_countries'):
                            countries = self.json.get(
                                'geographic_scope_countries')
                            if type(countries) == str:
                                countries = countries.split(',')
                            for country in countries:
                                if country.startswith('0x'):
                                    self.newsource['geographic_scope_countries'].append(
                                        UID(country))
                                else:
                                    # discard other data
                                    continue
                        self.parse_subunit()

                elif self.newsource['geographic_scope'] == 'national':
                    if self.json.get('geographic_scope_single'):
                        countries = []
                        if type(self.json.get('geographic_scope_single')) == str:
                            country = self.json.get('geographic_scope_single').split(',')
                        for item in country:
                            try:
                                if item.startswith('0x'):
                                    countries.append(UID(item))
                            except:
                                continue
                        self.newsource['geographic_scope_countries'] = countries

                elif self.newsource['geographic_scope'] == 'subnational':
                    if self.json.get('geographic_scope_single'):
                        countries = []
                        if type(self.json.get('geographic_scope_single')) == str:
                            country = self.json.get('geographic_scope_single').split(',')
                        for item in country:
                            try:
                                if item.startswith('0x'):
                                    countries.append(UID(item))
                            except:
                                continue
                        self.newsource['geographic_scope_countries'] = countries
                    else:
                        raise InventoryValidationError(
                            'Invalid Data! Please specify at least one country!')
                    self.parse_subunit()
            else:
                raise InventoryValidationError(
                    f'Invalid data! Unknown value in "geographic_scope": {self.json.get("geographic_scope")}')
        else:
            raise InventoryValidationError(
                'Invalid data! "geographic_scope" is required')

    def parse_subunit(self):
        """ if subunit is new, first we check its country and for potential duplication
            if the country is not in the Inventory, the subunit is rejected
            if it is duplicated, we use the existing entry
            finally, a new subunit is created and appended to the self.newsubunits list
        """
        if self.json.get('geographic_scope_subunit'):
            self.newsource['geographic_scope_subunit'] = []
            subunit_list = self.json.get('geographic_scope_subunit')
            if type(subunit_list) == str:
                subunit_list = subunit_list.split(',')

            for item in subunit_list:
                if item.strip().startswith('0x'):
                    self.newsource['geographic_scope_subunit'].append(
                        UID(item))
                else:
                    geo_query = self.resolve_subunit(item)
                    if geo_query:
                        self.newsource['geographic_scope_subunit'].append(
                            geo_query['uid'])

    def parse_languages(self):
        if self.json.get('languages'):
            languages = self.json.get('languages')
            if type(languages) == str:
                languages = self.json.get('languages').split(',')
            self.newsource['languages'] = [
                item.lower() for item in languages if item.lower() in icu_codes.keys()]

    def parse_audience_size(self):
        if self.json.get('audience_size_subscribers'):
            facets = {'copies_sold': int(
                self.json.get('audience_size_subscribers'))}
            if self.json.get('audience_size_datafrom'):
                facets['data_from'] = self.json.get(
                    'audience_size_datafrom')
            else:
                facets['data_from'] = "unknown"

            if self.json.get('audience_size_year'):
                audience_size_year = int(self.json.get('audience_size_year'))
            else:
                audience_size_year = datetime.date.today()

            self.newsource['audience_size'] = Scalar(
                audience_size_year, facets=facets)

    def fetch_siterankdata(self):
        daily_visitors = siterankdata(self.newsource['name'])

        if daily_visitors:
            self.newsource['audience_size'] = Scalar(datetime.date.today(), facets={
                'daily_visitors': daily_visitors,
                'data_from': f"https://siterankdata.com/{self.newsource['name'].replace('www.', '')}"})

    @staticmethod
    def source_unique_name(name, channel=None, channel_uid=None, country=None, country_uid=None):
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
        if self.newsource.get('geographic_scope_subunit'):
            current_app.logger.debug(
                self.newsource['geographic_scope_subunit'])
            if isinstance(self.newsource['geographic_scope_subunit'][0], UID):
                self.newsource["unique_name"] = self.source_unique_name(
                    self.json['name'], channel=self.json['channel'], country_uid=self.newsource['geographic_scope_subunit'][0])
            else:
                self.newsource["unique_name"] = self.source_unique_name(
                    self.json['name'], channel=self.json['channel'], country=self.newsubunits[0]['name'])

        elif len(self.newsource['geographic_scope_countries']) > 0:
            self.newsource["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country_uid=self.newsource['geographic_scope_countries'][0])
        else:
            self.newsource["unique_name"] = self.source_unique_name(
                self.json['name'], self.json['channel'], country="unknown")

    def parse_org(self):
        if self.json.get('publishes_org'):
            org_list = self.json.get('publishes_org')
            if type(org_list) == str:
                org_list = org_list.split(',')

            for item in org_list:
                org = {'publishes': self.newsource['uid'],
                       'is_person': False}
                if item.startswith('0x'):
                    org['uid'] = UID(item)

                else:
                    org = self.add_entry_meta(org)
                    org['uid'] = NewID(item)
                    org['name'] = item
                    org['dgraph.type'] = 'Organization'

                    try:
                        self.resolve_org(org)
                    except Exception as e:
                        current_app.logger.warning(e)

                    unique_name = slugify(item, separator="_")
                    if dgraph.get_uid('unique_name', unique_name):
                        unique_name += secrets.token_urlsafe(3)
                    org['unique_name'] = unique_name
                    
                self.orgs.append(org)

    def parse_person(self):
        if self.json.get('publishes_person'):
            person_list = self.json.get('publishes_person')
            if type(person_list) == str:
                person_list = person_list.split(',')

            for item in person_list:
                pers = {'publishes': self.newsource['uid'],
                        'is_person': True}
                if item.startswith('0x'):
                    pers['uid'] = UID(item)
                else:
                    pers = self.add_entry_meta(pers)
                    pers['name'] = item
                    pers['dgraph.type'] = "Organization"
                    unique_name = slugify(item, separator="_")
                    if dgraph.get_uid('unique_name', unique_name):
                        unique_name += secrets.token_urlsafe(3)
                    pers['unique_name'] = unique_name
               
                self.orgs.append(pers)

    def parse_archives(self):
        if self.json.get('archive_sources_included'):
            archive_list = self.json.get('archive_sources_included')
            if type(archive_list) == str:
                archive_list = archive_list.split(',')

            for item in archive_list:
                arch = {'sources_included': self.newsource['uid']}
                if item.startswith('0x'):
                    arch['uid'] = UID(item)

                else:
                    arch['uid'] = NewID(item)
                    arch = self.add_entry_meta(arch)
                    arch['name'] = item,
                    arch['dgraph.type'] = "Archive"
                self.archives.append(arch)

    def parse_datasets(self):
        if self.json.get('dataset_sources_included'):
            dataset_list = self.json.get('dataset_sources_included')
            if type(dataset_list) == str:
                dataset_list = dataset_list.split(',')

            for item in dataset_list:
                dset = {'sources_included': self.newsource['uid']}
                if item.startswith('0x'):
                    dset['uid'] = UID(item)

                else:
                    dset['uid'] = NewID(item)
                    dset = self.add_entry_meta(dset)
                    dset['name'] = item
                    dset['dgraph.type'] = "Dataset"
                self.archives.append(dset)

    def parse_entry_notes(self):
        if self.json.get('entry_notes'):
            self.newsource['entry_notes'] = self.json.get(
                'entry_notes').strip()

    def parse_related(self):
        if self.json.get('related_sources'):
            self.newsource['related'] = []
            related_list = self.json.get('related_sources')
            if type(related_list) == str:
                related_list = related_list.split(',')
            for item in related_list:
                rel_source = {'related': self.newsource['uid']}
                if item.startswith('0x'):
                    rel_source['uid'] = UID(item)
                    self.newsource['related'].append(UID(item))
                else:
                    if self.json.get(f'newsource_{item}'):
                        channel_name, channel_uid = self.json.get(
                            'newsource_' + item).split(',')
                        rel_source = self.add_entry_meta(
                            rel_source, entry_status="draft")
                        rel_source['name'] = item
                        rel_source['uid'] = NewID(
                            f'_:{slugify(item, separator="_")}_{channel_name}')
                        rel_source['unique_name'] = secrets.token_urlsafe(8)
                        rel_source['dgraph.type'] = 'Source'
                        rel_source['channel'] = UID(channel_uid)
                        if self.newsource.get('publication_kind'):
                            rel_source['publication_kind'] = self.newsource.get('publication_kind')
                        if self.newsource.get('special_interest'):
                            rel_source['special_interest'] = self.newsource.get('special_interest')
                        if self.newsource.get('topical_focus'):
                            rel_source['topical_focus'] = self.newsource.get('topical_focus')
                        if self.newsource.get('special_interest'):
                            rel_source['special_interest'] = self.newsource.get('special_interest')
                        if self.newsource.get('geographic_scope'):
                            rel_source['geographic_scope'] = self.newsource.get('geographic_scope')
                        if self.newsource.get('geographic_scope_countries'):
                            rel_source['geographic_scope_countries'] = self.newsource.get('geographic_scope_countries')
                        if self.newsource.get('geographic_scope_subunit'):
                            rel_source['geographic_scope_subunit'] = self.newsource.get('geographic_scope_subunit')
                        if self.newsource.get('languages'):
                            rel_source['languages'] = self.newsource.get('languages')
                        self.newsource['related'].append(
                            NewID(f'_:{slugify(item, separator="_")}_{channel_name}'))
                    else:
                        # just discard data if no channel is defined
                        continue
                self.related.append(rel_source)

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
            geo_data = Geolocation('Point', [
                float(geo_result.get('lon')), float(geo_result.get('lat'))])

            name = None
            other_names = [query]
            if geo_result['namedetails'].get('name'):
                other_names.append(geo_result['namedetails'].get('name'))
                name = geo_result['namedetails'].get('name')

            if geo_result['namedetails'].get('name:en'):
                other_names.append(geo_result['namedetails'].get('name:en'))
                name = geo_result['namedetails'].get('name:en')

            other_names = list(set(other_names))

            if not name:
                name = query

            new_subunit = {'name': name,
                           'country': UID(country_uid),
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
                geo_query = UID(duplicate_check)
            else:
                geo_query['uid'] = NewID(
                    f"_:{slugify(secrets.token_urlsafe(8))}")
            self.newsubunits.append(geo_query)

            return geo_query
        else:
            raise InventoryValidationError(
                f'Invalid Data! Could not resolve geographic subunit {subunit}')

    def parse_transcriptkind(self):
        if self.json.get('transcript_kind'):
            if self.json.get('transcript_kind') in self.transcript_kind:
                self.newsource['transcript_kind'] = self.json.get(
                    'transcript_kind')
            else:
                raise InventoryValidationError(
                    f"Invalid Data! Unknown value for transcript_kind: {self.json.get('transcript_kind')}")
        else:
            raise InventoryValidationError(
                f"Missing Data! transcript_kind is required!")

    def fetch_feeds(self):
        self.newsource['channel_feeds'] = []
        sitemaps = find_sitemaps(self.newsource['name'])
        if len(sitemaps) > 0:
            for sitemap in sitemaps:
                self.newsource['channel_feeds'].append(
                    Scalar(sitemap, facets={'kind': 'sitemap'}))

        feeds = find_feeds(self.newsource['name'])

        if len(feeds) > 0:
            for feed in feeds:
                self.newsource['channel_feeds'].append(
                    Scalar(feed, facets={'kind': 'rss'}))

    def fetch_instagram(self):
        if self.json.get('name'):
            profile = instagram(self.json.get('name').replace('@', ''))
            if profile:
                self.newsource['name'] = self.json.get(
                    'name').lower().replace('@', '')
                self.newsource['channel_url'] = self.json.get(
                    'name').lower().replace('@', '')
            else:
                raise InventoryValidationError(
                    f"Instagram profile not found: {self.json.get('name')}")

            if profile.get('fullname'):
                self.newsource['other_names'].append(profile['fullname'])
            if profile.get('followers'):
                facets = {'followers': int(
                    profile['followers'])}
                self.newsource['audience_size'] = Scalar(
                    str(datetime.date.today()), facets=facets)
            if profile.get('verified'):
                self.newsource['verified_account'] = profile['verified']

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    def fetch_twitter(self):
        if self.json.get('name'):
            self.newsource['channel_url'] = self.json.get(
                'name').replace('@', '')
            try:
                profile = twitter(self.json.get('name').replace('@', ''))
            except Exception as e:
                raise InventoryValidationError(
                    f"Twitter profile not found: {self.json.get('name')}. {e}")

            self.newsource['name'] = self.json.get(
                'name').lower().replace('@', '')

            if profile.get('fullname'):
                self.newsource['other_names'].append(profile['fullname'])
            if profile.get('followers'):
                facets = {'followers': int(
                    profile['followers'])}
                self.newsource['audience_size'] = Scalar(
                    str(datetime.date.today()), facets=facets)
            if profile.get('joined'):
                self.newsource['founded'] = profile.get('joined').isoformat()
            if profile.get('verified'):
                self.newsource['verified_account'] = profile.get('verified')

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')
    
    def fetch_vk(self):
        if self.json.get('name'):
            self.newsource['channel_url'] = self.json.get(
                'name').replace('@', '')
            try:
                profile = vkontakte(self.json.get('name').replace('@', ''))
            except Exception as e:
                raise InventoryValidationError(
                    f"VKontakte profile not found: {self.json.get('name')}. {e}")

            self.newsource['name'] = self.json.get(
                'name').lower().replace('@', '')

            if profile.get('fullname'):
                self.newsource['other_names'].append(profile['fullname'])
            if profile.get('followers'):
                facets = {'followers': int(
                    profile['followers'])}
                self.newsource['audience_size'] = Scalar(
                    str(datetime.date.today()), facets=facets)
            if profile.get('verified'):
                self.newsource['verified_account'] = profile.get('verified')
            if profile.get('description'):
                self.newsource['description'] = profile.get('description')

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')
                

    def resolve_org(self, org):

        geo_result = geocode(org['name'])
        if geo_result:
            try:
                org['address_geo'] = Geolocation('Point', [
                    float(geo_result.get('lon')), float(geo_result.get('lat'))])
            except:
                pass
            try:
                address_lookup = reverse_geocode(geo_result.get('lat'), geo_result.get('lon'))
                org['address_string'] = address_lookup['display_name']
            except:
                pass

        wikidata = get_wikidata(org['name'])

        if wikidata:
            for key, val in wikidata.items():
                if key not in org.keys():
                    org[key] = val
        
        return org







    def fetch_facebook(self):
        if self.json.get('name'):
            self.newsource['channel_url'] = self.json.get('name')
            self.newsource['name'] = self.json.get('name')
            # try:
            #     profile = facebook(self.json.get('name'))
            # except Exception as e:
            #     raise InventoryValidationError(
            #         f"Facebook profile not found: {self.json.get('name')}. {e}")

            # self.newsource['name'] = self.json.get('name').lower()

            # if profile.get('fullname'):
            #     self.newsource['other_names'].append(profile['fullname'])
            # if profile.get('followers'):
            #     self.newsource['audience_size'] = str(datetime.date.today())
            #     self.newsource['audience_size|followers'] = int(
            #         profile['followers'])
            # if profile.get('joined'):
            #     self.newsource['founded'] = profile.get('joined').isoformat()

        else:
            raise InventoryValidationError(
                'Invalid data! "name" not specified.')

    # unique names of related & new sources are generated later (after reviewed)
