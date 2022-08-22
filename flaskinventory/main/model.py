import datetime
from typing import Union
from flask import current_app
from flaskinventory import dgraph
from flaskinventory.errors import InventoryPermissionError, InventoryValidationError
from flaskinventory.flaskdgraph.dgraph_types import (MutualListRelationship, String, Integer, Boolean, UIDPredicate,
                                                     SingleChoice, MultipleChoice,
                                                     DateTime, Year, GeoScalar,
                                                     ListString, ListRelationship,
                                                     Geo, SingleRelationship, UniqueName,
                                                     ReverseRelationship, ReverseListRelationship, 
                                                     NewID, UID, Scalar)


from flaskinventory.add.external import geocode, reverse_geocode, get_wikidata
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.utils import validate_uid
from flaskinventory.auxiliary import icu_codes, programming_languages

from slugify import slugify
import secrets

"""
    Custom Fields
"""


class GeoAutoCode(Geo):

    autoinput = 'address_string'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def autocode(self, data, **kwargs) -> Union[GeoScalar, None]:
        return self.str2geo(data)


class AddressAutocode(Geo):

    autoinput = 'name'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(overwrite=True, *args, **kwargs)

    def validation_hook(self, data):
        return str(data)

    def autocode(self, data: str, **kwargs) -> Union[dict, None]:
        query_result = self.str2geo(data)
        geo_result = None
        if query_result:
            geo_result = {'address_geo': query_result}
            address_lookup = reverse_geocode(
                query_result.lat, query_result.lon)
            geo_result['address_string'] = address_lookup.get('display_name')
        return geo_result


class SourceCountrySelection(ListRelationship):

    """
        Special field with constraint to only include countries with Scope of OPTED
    """

    def __init__(self, *args, **kwargs) -> None:

        super().__init__(relationship_constraint = ['Multinational', 'Country'], 
                            allow_new=False, autoload_choices=True, 
                            overwrite=True, *args, **kwargs)

    def get_choices(self):

        query_country = '''country(func: type("Country"), orderasc: name) @filter(eq(opted_scope, true)) { uid unique_name name  }'''
        query_multinational = '''multinational(func: type("Multinational"), orderasc: name) { uid unique_name name other_names }'''

        query_string = '{ ' + query_country + query_multinational + ' }'

        choices = dgraph.query(query_string=query_string)

        if len(self.relationship_constraint) == 1:
            self.choices = {c['uid']: c['name'] for c in choices[self.relationship_constraint[0].lower()]}
            self.choices_tuples = [(c['uid'], c['name']) for c in choices[self.relationship_constraint[0].lower()]]

        else:
            self.choices = {}
            self.choices_tuples = {}
            for dgraph_type in self.relationship_constraint:
                self.choices_tuples[dgraph_type] = [(c['uid'], c['name']) for c in choices[dgraph_type.lower()]]
                self.choices.update({c['uid']: c['name'] for c in choices[dgraph_type.lower()]})


class SubunitAutocode(ListRelationship):

    def __init__(self, *args, **kwargs) -> None:

        super().__init__(relationship_constraint = ['Subunit'], 
                            allow_new=True, autoload_choices=True, 
                            overwrite=True, *args, **kwargs)
        
    def get_choices(self):

        query_string = '''{
                            q(func: type(Country)) {
                            name
                                subunit: ~country @filter(type(Subunit)) {
                                        name uid
                                }
                            }
                        }
                        '''

        choices = dgraph.query(query_string=query_string)

        self.choices = {}
        self.choices_tuples = {}

        for country in choices["q"]:
            if country.get('subunit'):
                self.choices_tuples[country['name']] = [(s['uid'], s['name']) for s in country['subunit']]
                self.choices.update({s['uid']: s['name'] for s in country['subunit']})


    def _geo_query_subunit(self, query):
        geo_result = geocode(query)
        if geo_result:
            current_app.logger.debug(f'Got a result for "{query}": {geo_result}')
            dql_string = '''
            query get_country($country_code: string) {
                q(func: eq(country_code, $country_code)) @filter(type("Country")) { uid } 
                }'''
            dql_result = dgraph.query(dql_string, variables={'$country_code': geo_result['address']['country_code']})
            try:
                country_uid = dql_result['q'][0]['uid']
            except Exception:
                raise InventoryValidationError(
                    f"Error in <{self.predicate}>! While parsing {query} no matching country found in inventory: {geo_result['address']['country_code']}")
            geo_data = GeoScalar('Point', [
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

            if name in other_names:
                other_names.remove(name)

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
                                f'<{self.predicate}>: Could not parse wikidata ID in subunit "{query}": {e}')

            return new_subunit
        else:
            return False

    def _resolve_subunit(self, subunit):
        geo_query = self._geo_query_subunit(subunit)
        if geo_query:
            current_app.logger.debug(f'parsing result of querying {subunit}: {geo_query}')
            geo_query['dgraph.type'] = ['Subunit']
            # prevent duplicates
            geo_query['unique_name'] = f"{slugify(subunit, separator='_')}_{geo_query['country_code']}"
            duplicate_check = dgraph.get_uid(
                'unique_name', geo_query['unique_name'])
            if duplicate_check:
                geo_query = {'uid': UID(duplicate_check)}
            else:
                geo_query['uid'] = NewID(
                    f"_:{slugify(secrets.token_urlsafe(8))}")
            return geo_query
        else:
            raise InventoryValidationError(
                f'Invalid Data! Could not resolve geographic subunit {subunit}')

    def validation_hook(self, data):
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! provided value is not a UID: {data}')
            current_app.logger.debug(f'New subunit, trying to resolve "{data}"')
            new_subunit = self._resolve_subunit(data)
            return new_subunit
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type not in self.relationship_constraint:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! UID specified does not match constrain, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')        
        return {'uid': UID(uid)}

    def validate(self, data, facets=None) -> list:
        if isinstance(data, str):
            data = data.split(',')
        data = set([item.strip() for item in data if item.strip() != ''])
        uids = []
        for item in data:
            uid = self.validation_hook(item)
            if uid:
                uids.append(uid)

        return uids
        

class OrganizationAutocode(ReverseListRelationship):

    def __init__(self, predicate_name, *args, **kwargs) -> None:

        super().__init__(predicate_name,
                            relationship_constraint = 'Organization', 
                            allow_new=True, 
                            autoload_choices=False, 
                            overwrite=True, 
                            *args, **kwargs)

    def validation_hook(self, data, node, facets=None):
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in <{self._predicate}>! provided value is not a UID: {data}')
            new_org = {'uid': NewID(data, facets=facets), self._target_predicate: node, 'name': data}
            new_org = self._resolve_org(new_org)
            if self.default_predicates:
                new_org.update(self.default_predicates)
            return new_org
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type not in self.relationship_constraint:
                raise InventoryValidationError(
                    f'Error in <{self._predicate}>! UID specified does not match constrain, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')        
        return {'uid': UID(uid, facets=facets), self._target_predicate: node}

    def validate(self, data, node, facets=None) -> Union[UID, NewID, dict]:
        if isinstance(data, str):
            data = data.split(',')

        data = set([item.strip() for item in data])
        uids = []

        for item in data:
            uid = self.validation_hook(item, node, facets=facets)
            uids.append(uid)
        
        return uids

    def _resolve_org(self, org):

        geo_result = geocode(org['name'])
        if geo_result:
            try:
                org['address_geo'] = GeoScalar('Point', [
                    float(geo_result.get('lon')), float(geo_result.get('lat'))])
            except:
                pass
            try:
                address_lookup = reverse_geocode(
                    geo_result.get('lat'), geo_result.get('lon'))
                org['address_string'] = address_lookup['display_name']
            except:
                pass

        wikidata = get_wikidata(org['name'])

        if wikidata:
            for key, val in wikidata.items():
                if key not in org.keys():
                    org[key] = val
        
        if self.relationship_constraint:
            org['dgraph.type'] = self.relationship_constraint
            
        return org


class OrderedListString(ListString):

    def validate(self, data, facets=None, **kwargs):
        data = self.validation_hook(data)
        ordered_data = []
        if not facets:
            facets = {"sequence": 0}
        if isinstance(data, (list, set, tuple)):
            for i, item in enumerate(data):
                f = facets.copy()
                f.update(sequence=i)
                if isinstance(item, (str, int, datetime.datetime, datetime.date)):
                    ordered_data.append(Scalar(item, facets=f))
                elif hasattr(item, "facets"):
                    ordered_data.append(item.update_facets(f))
                else:
                    raise InventoryValidationError(
                        f'Error in <{self.predicate}>! Do not know how to handle {type(item)}. Value: {item}')
            return ordered_data
        elif isinstance(data, (str, int, datetime.datetime, datetime.date)):
            return Scalar(data, facets=facets)
        elif hasattr(data, facets):
            data.update_facets(facets)
            return data
        else:
            raise InventoryValidationError(
                f'Error in <{self.predicate}>! Do not know how to handle {type(data)}. Value: {data}')
       
class MultipleChoiceInt(MultipleChoice):

    dgraph_predicate_type = '[int]'

    def validation_hook(self, data):
        if isinstance(data, str):
            data = data.split(',')
        if not isinstance(data, list):
            raise InventoryValidationError(
                f'Error in <{self.predicate}>! Provided data cannot be coerced to "list": {data}')
        for val in data:
            if val.strip() not in self.values:
                raise InventoryValidationError(
                    f"Wrong value provided for {self.predicate}: {val}. Value has to be one of {', '.join(self.values)}")
            if val.strip().lower() == 'na':
                data = None

        return data


class GitHubAuto(String):

    def validation_hook(self, data):
        if "github" in data:
            data = data.replace('https://www.', '')
            data = data.replace('http://www.', '')
            data = data.replace('https://', '')
            data = data.replace('http://', '')
            data = data.replace('github.com/', '')
            if data.startswith('/'):
                data = data[1:]
        
        return data

"""
    Entry
"""


class Entry(Schema):

    __permission_new__ = USER_ROLES.Contributor
    __permission_edit__ = USER_ROLES.Contributor

    uid = UIDPredicate()
    
    unique_name = UniqueName()
    
    name = String(required=True)
    
    other_names = ListString()
    
    wikidataID = Integer(label='WikiData ID',
                         overwrite=True,
                         new=False)

    description = String(large_textfield=True, queryable=True, comparison_operator="alloftext")

    entry_notes = String(description='Do you have any other notes on the entry that you just coded?',
                         large_textfield=True)
    
    entry_review_status = SingleChoice(choices={'draft': 'Draft',
                                                'pending': 'Pending',
                                                'accepted': 'Accepted',
                                                'rejected': 'Rejected'},
                                       default='pending',
                                       required=True,
                                       new=False,
                                       permission=USER_ROLES.Reviewer)


class Organization(Entry):

    name = String(label='Organization Name',
                  required=True,
                  description='What is the legal or official name of the media organisation?',
                  render_kw={'placeholder': 'e.g. The Big Media Corp.'})
    
    other_names = ListString(description='Does the organisation have any other names or common abbreviations?',
                             render_kw={'placeholder': 'Separate by comma'})
    
    is_person = Boolean(label='Yes, is a person',
                        description='Is the media organisation a person?',
                        queryable=True)
    
    ownership_kind = SingleChoice(choices={
                                    'NA': "Don't know / NA",
                                    'private ownership': 'Mainly private Ownership',
                                    'public ownership': 'Mainly public ownership',
                                    'political party': 'Political Party',
                                    'unknown': 'Unknown Ownership'},
                                  description='Is the media organization mainly privately owned or publicly owned?',
                                  queryable=True)

    country = SingleRelationship(relationship_constraint='Country', 
                                 allow_new=False,
                                 overwrite=True,
                                 autoload_choices=True, 
                                 description='In which country is the organisation located?',
                                 render_kw={'placeholder': 'Select a country...'},
                                 queryable=True)
    
    publishes = ListRelationship(allow_new=False, 
                                 relationship_constraint='Source', 
                                 overwrite=True, 
                                 description='Which news sources publishes the organisation (or person)?',
                                 render_kw={'placeholder': 'Type to search existing news sources and add multiple...'})
    
    owns = ListRelationship(allow_new=False,
                            relationship_constraint='Organization',
                            overwrite=True,
                            description='Which other media organisations are owned by this new organisation (or person)?',
                            render_kw={'placeholder': 'Type to search existing organisations and add multiple...'})

    party_affiliated = SingleChoice(choices={
                                        'NA': "Don't know / NA",
                                        'yes': 'Yes',
                                        'no': 'No'
                                    },
                                    new=False,
                                    queryable=True)
    
    address_string = AddressAutocode(new=False,
                                     render_kw={'placeholder': 'Main address of the organization.'})
    
    address_geo = GeoAutoCode(read_only=True, new=False, edit=False, hidden=True)
    
    employees = String(description='How many employees does the news organization have?',
                       render_kw={
                           'placeholder': 'Most recent figure as plain number'},
                       new=False)
    
    founded = DateTime(new=False, overwrite=True, queryable=True)



class Source(Entry):

    channel = SingleRelationship(description='Through which channel is the news source distributed?',
                                 edit=False,
                                 allow_new=False,
                                 autoload_choices=True,
                                 relationship_constraint='Channel',
                                 read_only=True,
                                 required=True,
                                 queryable=True,
                                 predicate_alias=['channels'])

    name = String(label='Name of the News Source',
                  required=True,
                  description='What is the name of the news source?',
                  render_kw={'placeholder': "e.g. 'The Royal Gazette'"})

    channel_url = String(label='URL of Channel',
                         description="What is the url or social media handle of the news source?")
    
    verified_account = Boolean(new=False, edit=False, queryable=True)

    other_names = ListString(description='Is the news source known by alternative names (e.g. Krone, Die Kronen Zeitung)?',
                             render_kw={'placeholder': 'Separate by comma'}, 
                             overwrite=True)
    
    transcript_kind = SingleChoice(description="What kind of show is transcribed?",
                                    choices={'tv':  "TV (broadcast, cable, satellite, etc)",
                                             'radio': "Radio",
                                             "podcast": "Podcast",
                                             "NA": "Don't know / NA"},
                                    queryable=True)

    website_allows_comments = SingleChoice(description='Does the online news source have user comments below individual news articles?',
                                           choices={'yes': 'Yes',
                                                    'no': 'No',
                                                    'NA': "Don't know / NA"},
                                            queryable=True)

    website_comments_registration_required = SingleChoice(label="Registraion required for posting comments",
                                                          description='Is a registration or an account required to leave comments?',
                                                          choices={'yes': 'Yes',
                                                                    'no': 'No',
                                                                    'NA': "Don't know / NA"})

    founded = Year(description="What year was the news source founded?", 
                    overwrite=True,
                    queryable=True)

    publication_kind = MultipleChoice(description='What label or labels describe the main source?',
                                      choices={'newspaper': 'Newspaper / News Site', 
                                                'news agency': 'News Agency', 
                                                'magazine': 'Magazine', 
                                                'tv show': 'TV Show / TV Channel', 
                                                'radio show': 'Radio Show / Radio Channel', 
                                                'podcast': 'Podcast', 
                                                'news blog': 'News Blog', 
                                                'alternative media': 'Alternative Media'},
                                        tom_select=True,
                                        required=True,
                                        queryable=True)

    special_interest = Boolean(description='Does the news source have one main topical focus?',
                                label='Yes, is a special interest publication',
                                queryable=True)
    
    topical_focus = MultipleChoice(description="What is the main topical focus of the news source?",
                                    choices={'politics': 'Politics', 
                                             'society': 'Society & Panorama', 
                                             'economy': 'Business, Economy, Finance & Stocks', 
                                             'religion': 'Religion', 
                                             'science': 'Science & Technology', 
                                             'media': 'Media', 
                                             'environment': 'Environment', 
                                             'education': 'Education'},
                                    tom_select=True,
                                    queryable=True)
    
    publication_cycle = SingleChoice(description="What is the publication cycle of the source?",
                                        choices={'continuous': 'Continuous', 
                                                 'daily': 'Daily (7 times a week)', 
                                                 'multiple times per week': 'Multiple times per week', 
                                                 'weekly': 'Weekly', 
                                                 'twice a month': 'Twice a month', 
                                                 'monthly': 'Monthly', 
                                                 'less than monthly': 'Less frequent than monthly', 
                                                 'NA': "Don't Know / NA"},
                                                 required=True,
                                        queryable=True)

    publication_cycle_weekday = MultipleChoiceInt(description="Please indicate the specific day(s) when the news source publishes.",
                                                choices={"1": 'Monday', 
                                                        "2": 'Tuesday', 
                                                        "3": 'Wednesday', 
                                                        "4": 'Thursday', 
                                                        "5": 'Friday', 
                                                        "6": 'Saturday', 
                                                        "7": 'Sunday', 
                                                        'NA': "Don't Know / NA"},
                                                tom_select=True)

    geographic_scope = SingleChoice(description="What is the geographic scope of the news source?",
                                    choices={'multinational': 'Multinational', 
                                             'national': 'National', 
                                             'subnational': 'Subnational', 
                                             'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True,
                                    queryable=True)

    country = SourceCountrySelection(label='Countries', 
                                        description='Which countries are in the geographic scope?',
                                        required=True,
                                        queryable=True)

    geographic_scope_subunit = SubunitAutocode(label='Subunits',
                                                description='What is the subnational scope?',
                                                tom_select=True,
                                                queryable=True)

    languages = MultipleChoice(description="In which language(s) does the news source publish its news texts?",
                                required=True,
                                choices=icu_codes,
                                tom_select=True,
                                queryable=True)

    payment_model = SingleChoice(description="Is the content produced by the news source accessible free of charge?",
                                    choices={'free': 'All content is free of charge', 
                                            'partly free': 'Some content is free of charge', 
                                            'not free': 'No content is free of charge', 
                                            'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True,
                                    queryable=True)

    contains_ads = SingleChoice(description="Does the news source contain advertisements?",
                                    choices={'yes': 'Yes', 
                                                'no': 'No', 
                                                'non subscribers': 'Only for non-subscribers', 
                                                'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True,
                                    queryable=True)

    audience_size = Year(default=datetime.date.today(), edit=False, queryable=True)

    publishes_org = OrganizationAutocode('publishes', 
                                       label='Published by',
                                       default_predicates={'is_person': False})

    publishes_person = OrganizationAutocode('publishes', 
                                       label='Published by person',
                                       default_predicates={'is_person': True})

    channel_epaper = SingleChoice(description='Does the print news source have an e-paper version?',
                                    choices={'yes': 'Yes',
                                            'no': 'No',
                                            'NA': "Don't know / NA"},
                                    queryable=True)

    archive_sources_included = ReverseListRelationship('sources_included', 
                                                    allow_new=False, 
                                                    relationship_constraint='Archive',
                                                    description="Are texts from the news source available for download in one or several of the following data archives?",
                                                    label='News source included in these archives')
    
    dataset_sources_included = ReverseListRelationship('sources_included', 
                                                    allow_new=False, 
                                                    relationship_constraint='Dataset',
                                                    description="Is the news source included in one or several of the following annotated media text data sets?",
                                                    label='News source included in these datasets')

    corpus_sources_included = ReverseListRelationship('sources_included', 
                                                    allow_new=False, 
                                                    relationship_constraint='Corpus',
                                                    description="Is the news source included in one or several of the following corpora?",
                                                    label='News source included in these corpora')


    party_affiliated = SingleChoice(description='Is the news source close to a political party?',
                                    choices={'NA': "Don't know / NA",
                                            'yes': 'Yes',
                                            'no': 'No',
                                            },
                                    queryable=True)
    
    defunct = Boolean(description="Is the news source defunct or out of business?",
                        queryable=True) 

    related = MutualListRelationship(allow_new=True, autoload_choices=False, relationship_constraint='Source')



class Channel(Entry):

    __permission_new__ = USER_ROLES.Admin
    __permission_edit__ = USER_ROLES.Admin

class Country(Entry):

    __permission_new__ = USER_ROLES.Admin
    __permission_edit__ = USER_ROLES.Admin

    country_code = String(permission=USER_ROLES.Admin)
    opted_scope = Boolean(description="Is country in the scope of OPTED?",
                            label='Yes, in scope of OPTED')

class Multinational(Entry):

    __permission_new__ = USER_ROLES.Admin
    __permission_edit__ = USER_ROLES.Admin

    description = String(large_textfield=True)

class Subunit(Entry):

    __permission_new__ = USER_ROLES.Reviewer
    __permission_edit__ = USER_ROLES.Reviewer

    country = SingleRelationship(required=True, 
                                tom_select=True,
                                autoload_choices=True, 
                                overwrite=True,
                                relationship_constraint='Country')
    country_code = String()
    location_point = Geo(edit=False, new=False)

class Archive(Entry):

    name = String(description="What is the name of the archive?", required=True)

    other_names = ListString(description="Does the archive have other names?",
                            render_kw={'placeholder': 'Separate by comma ","'},
                            overwrite=True)

    description = String(large_textfield=True)

    url = String()

    access = SingleChoice(choices={'free': 'Free',
                                    'restricted': 'Restricted'})
    sources_included = ListRelationship(relationship_constraint='Source', allow_new=False)
    fulltext = Boolean(description='Archive contains fulltext')
    country = ListRelationship(relationship_constraint=['Country', 'Multinational'], autoload_choices=True)
    text_units = ListRelationship(description="List of text units available in the data archive (e.g., sentences, paragraphs, tweets, news articles, summaries, headlines)",
                                    relationship_constraint="TextUnit",
                                    render_kw={'placeholder': 'Select multiple...'},
                                    autoload_choices=True)

class Dataset(Entry):

    name = String(description="What is the name of the dataset?", required=True)

    other_names = ListString(description="Does the dataset have other names?",
                            render_kw={'placeholder': 'Separate by comma ","'},
                            overwrite=True)

    authors = OrderedListString(delimiter=';',
                            render_kw={'placeholder': 'Separate by semicolon ";"'}, tom_select=True,
                            required=True)
                            
    published_date = Year(label='Year of publication', 
                            description="Which year was the dataset published?")
    
    last_updated = DateTime(description="When was the dataset last updated?", new=False)

    url = String(label="URL", description="Link to the dataset", required=True)
    doi = String(label='DOI')
    arxiv = String(label="arXiv")

    description = String(large_textfield=True, description="Please provide a short description for the tool")


    access = SingleChoice(choices={'free': 'Free',
                                    'restricted': 'Restricted'})
    
    country = ListRelationship(description="Does the dataset have a specific geographic coverage?",
                                relationship_constraint=['Country', 'Multinational'], 
                                autoload_choices=True,
                                render_kw={'placeholder': 'Select multiple countries...'})

    languages = MultipleChoice(description="Which languages are covered in the dataset?",
                                choices=icu_codes,
                                tom_select=True,
                                render_kw={'placeholder': 'Select multiple...'})

    start_date = DateTime(description="Start date of the dataset")

    end_date = DateTime(description="End date of the dataset")

    file_format = ListRelationship(description="In which file format(s) is the dataset stored?",
                                        autoload_choices=True,
                                        relationship_constraint="FileFormat",
                                        render_kw={'placeholder': 'Select multiple...'})

    sources_included = ListRelationship(relationship_constraint='Source', allow_new=False,
                                            render_kw={'placeholder': 'Select multiple...'})

    materials = ListString(description="Are there additional materials for the dataset? (e.g., codebook, documentation, etc)",
                            tom_select=True, render_kw={'placeholder': 'please paste the URLs to the materials here!'})

    initial_source = ListRelationship(description="If the dataset is derived from another corpus or dataset, the original source can be linked here",
                                        relationship_constraint=['Dataset', 'Corpus'],
                                        render_kw={'placeholder': 'Select multiple...'})

    meta_vars = ListRelationship(description="List of meta data included in the dataset (e.g., date, language, source, medium)",
                                    relationship_constraint="MetaVar",
                                    render_kw={'placeholder': 'Select multiple...'},
                                    autoload_choices=True)

    concept_vars = ListRelationship(description="List of variables based on concepts (e.g. sentiment, frames, etc)",
                                        relationship_constraint="ConceptVar",
                                        render_kw={'placeholder': 'Select multiple...'},
                                        autoload_choices=True)


class Corpus(Entry):

    name = String(description="What is the name of the corpus?", required=True)

    other_names = ListString(description="Does the corpus have other names?",
                            render_kw={'placeholder': 'Separate by comma ","'},
                            overwrite=True)

    authors = OrderedListString(delimiter=';',
                            render_kw={'placeholder': 'Separate by semicolon ";"'}, tom_select=True,
                            required=True)
                            
    published_date = Year(label='Year of publication', 
                            description="Which year was the corpus published?")
    
    last_updated = DateTime(description="When was the corpus last updated?", new=False)

    url = String(label="URL", description="Link to the corpus", required=True)
    doi = String(label='DOI')
    arxiv = String(label="arXiv")

    description = String(large_textfield=True, description="Please provide a short description for the corpus")

    access = SingleChoice(choices={'free': 'Free',
                                    'restricted': 'Restricted'})
    
    country = ListRelationship(description="Does the corpus have a specific geographic coverage?",
                                relationship_constraint=['Country', 'Multinational'], 
                                autoload_choices=True,
                                render_kw={'placeholder': 'Select multiple countries...'})

    languages = MultipleChoice(description="Which languages are covered in the corpus?",
                                choices=icu_codes,
                                tom_select=True,
                                render_kw={'placeholder': 'Select multiple...'})

    start_date = DateTime(description="Start date of the corpus")

    end_date = DateTime(description="End date of the corpus")

    file_format = ListRelationship(description="In which file format(s) is the corpus stored?",
                                        autoload_choices=True,
                                        relationship_constraint="FileFormat",
                                        render_kw={'placeholder': 'Select multiple...'})

    materials = ListString(description="Are there additional materials for the corpus? (e.g., codebook, documentation, etc)",
                            tom_select=True, render_kw={'placeholder': 'please paste the URLs to the materials here!'})

    sources_included = ListRelationship(relationship_constraint='Source', allow_new=False,
                                            render_kw={'placeholder': 'Select multiple...'})

    text_units = ListRelationship(description="List of text units included in the corpus (e.g., sentences, paragraphs, tweets, news articles, summaries, headlines)",
                                    relationship_constraint="TextUnit",
                                    render_kw={'placeholder': 'Select multiple...'},
                                    autoload_choices=True)

    meta_vars = ListRelationship(description="List of meta data included in the corpus (e.g., date, language, source, medium)",
                                    relationship_constraint="MetaVar",
                                    render_kw={'placeholder': 'Select multiple...'},
                                    autoload_choices=True)

    concept_vars = ListRelationship(description="List of annotations included in the corpus (e.g., sentiment, topic, named entities)",
                                        relationship_constraint="ConceptVar",
                                        render_kw={'placeholder': 'Select multiple...'},
                                        autoload_choices=True)

    initial_source = ListRelationship(description="If the corpus is derived from another corpus or dataset, the original source can be linked here",
                                        relationship_constraint=['Dataset', 'Corpus'],
                                        render_kw={'placeholder': 'Select multiple...'})



class Tool(Entry):

    name = String(description="What is the name of the tool?", required=True)

    other_names = ListString(description="Does the tool have other names?",
                            render_kw={'placeholder': 'Separate by comma ","'},
                            overwrite=True)

    authors = OrderedListString(delimiter=';',
                            render_kw={'placeholder': 'Separate by semicolon ";"'}, tom_select=True,
                            required=True)
                            
    published_date = Year(label='Year of publication', 
                            description="Which year was the tool published?",
                            queryable=True)
    
    last_updated = DateTime(description="When was the tool last updated?", new=False)

    url = String(label="URL", description="Link to the tool", required=True)
    doi = String(label='DOI',
                    overwrite=True)
    arxiv = String(label='arXiv',
                    overwrite=True)
    cran = String(label="CRAN", description="CRAN Package name",
                    render_kw={'placeholder': 'usually this is filled in automatically...'},
                    overwrite=True)
    
    pypi = String(label="PyPi", description="PyPi Project name",
                    render_kw={'placeholder': 'usually this is filled in automatically...'},
                    overwrite=True)

    github = GitHubAuto(label="Github", description="Github repository",
                        render_kw={'placeholder': 'If the tool has a repository on Github you can add this here.'},
                    overwrite=True)

    description = String(large_textfield=True, description="Please provide a short description for the tool",
                    overwrite=True)

    platform = MultipleChoice(description="For which kind of operating systems is the tool available?",
                                    choices={'windows': 'Windows', 
                                            'linux': 'Linux', 
                                            'macos': 'macOS'},
                                    required=True,
                                    tom_select=True,
                                    queryable=True)

    programming_languages = MultipleChoice(label="Programming Languages",
                                            description="Which programming languages are used for the tool? \
                                            Please also include language that can directly interface with this tool.",
                                           choices=programming_languages,
                                           required=False,
                                            tom_select=True,
                                            queryable=True)

    open_source = SingleChoice(description="Is this tool open source?",
                                choices={'na': 'NA / Unknown',
                                        'yes': 'Yes',
                                        'no': 'No, proprietary'},
                                queryable=True)

    license = String(description="What kind of license attached to the tool?")

    user_access = SingleChoice(description="How can the user access the tool?",
                                choices={'na': 'NA / Unknown',
                                        'free': 'Free',
                                        'registration': 'Registration',
                                        'request': 'Upon Request',
                                        'purchase': 'Purchase'},
                                queryable=True)

    used_for = ListRelationship(description="Which operations can the tool perform?",
                                relationship_constraint="Operation",
                                autoload_choices=True,
                                required=True,
                                queryable=True)

    concept_vars = ListRelationship(description="Which concepts can the tool measuere (e.g. sentiment, frames, etc)",
                                        relationship_constraint="ConceptVar",
                                        render_kw={'placeholder': 'Select multiple...'},
                                        autoload_choices=True,
                                        queryable=True)

    graphical_user_interface = Boolean(description="Does the tool have a graphical user interface?",
                                        label="Yes, it does have a GUI",
                                        default=False,
                                        queryable=True)

    channels = ListRelationship(description="Is the tool designed for specific channels?",
                                autoload_choices=True,
                                allow_new=False,
                                relationship_constraint="Channel")

    language_independent = Boolean(description="Is the tool language independent?",
                                    label="Yes",
                                    queryable=True)

    languages = MultipleChoice(description="Which languages does the tool support?",
                                choices=icu_codes,
                                tom_select=True,
                                queryable=True)

    input_file_format = ListRelationship(description="Which file formats does the tool take as input?",
                                        autoload_choices=True,
                                        relationship_constraint="FileFormat",
                                        queryable=True)

    output_file_format = ListRelationship(description="Which file formats does the tool output?",
                                        autoload_choices=True,
                                        relationship_constraint="FileFormat",
                                        queryable=True)

    author_validated = SingleChoice(description="Do the authors of the tool report any validation?",
                                    choices={'na': 'NA / Unknown',
                                            'yes': 'Yes',
                                            'no': 'No, not reported'},
                                    queryable=True)

    validation_corpus = ListRelationship(description="Which corpus was used to validate the tool?",
                                            autoload_choices=True,
                                            relationship_constraint="Corpus",
                                            queryable=True)

    materials = ListString(description="Are there additional materials for the tool? (e.g., FAQ, Tutorials, Website, etc)",
                            tom_select=True, render_kw={'placeholder': 'please paste the URLs to the materials here!'})

    related_publications = ReverseListRelationship('tools_used', 
                                            description="Which research publications are using this tool?",
                                            autoload_choices=True,
                                            allow_new=False,
                                            new=False,
                                            relationship_constraint="ResearchPaper")

    defunct = Boolean(description="Is the tool defunct?", queryable=True) 


class ResearchPaper(Entry):

    name = String(new=False, edit=False, hidden=True)
    other_names = ListString(new=False, edit=False, hidden=True, required=False)

    title = String(description="What is the title of the publication?", required=True)

    authors = OrderedListString(delimiter=';',
                            render_kw={'placeholder': 'Separate by semicolon ";"'}, tom_select=True,
                            required=True)
                            
    published_date = Year(label='Year of publication', 
                            description="Which year was the publication published?",
                            required=True)

    paper_kind = String(description="What kind of publcation is this? (e.g., Journal article, book section)")
    
    journal = String(description="In which journal was it published?")
    
    url = String(label="URL", description="Link to the publication", required=True)
    doi = String(label='DOI')
    arxiv = String(label='arXiv')

    description = String(large_textfield=True, description="Abstract or a short description of the publication")

    tools_used = ListRelationship(description="Which research tool(s) where used in the publication?",
                                            autoload_choices=True,
                                            allow_new=False,
                                            relationship_constraint="Tool")

    sources_included = ListRelationship(description="Which news sources are investigated in this publication?",
                                            autoload_choices=False,
                                            allow_new=False,
                                            relationship_constraint="Source")

    text_units = ListRelationship(description="List of text units analysed in the publication (e.g., sentences, paragraphs, tweets, news articles, summaries, headlines)",
                                    relationship_constraint="TextUnit",
                                    render_kw={'placeholder': 'Select multiple...'},
                                    autoload_choices=True)
    
    datasets_used = ListRelationship(description="Which dataset(s) where used in the publication?",
                                            autoload_choices=True,
                                            allow_new=False,
                                            relationship_constraint="Dataset")

    corpus_used = ListRelationship(description="Which corpora where used in the publication?",
                                            autoload_choices=True,
                                            allow_new=False,
                                            relationship_constraint="Corpus")

    country = ListRelationship(description="Does the publication have some sort of country that it focuses on?",
                                                autoload_choices=True,
                                                allow_new=False,
                                                relationship_constraint="Country")



    
""" Tag Like Types """

class Operation(Entry):

    pass

class FileFormat(Entry):

    pass

class MetaVar(Entry):
    
    pass

class ConceptVar(Entry):
    
    pass

class TextUnit(Entry):
    
    pass

