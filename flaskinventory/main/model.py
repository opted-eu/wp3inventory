from typing import List
from flaskinventory.flaskdgraph.dgraph_types import (String, Integer, Boolean, UIDPredicate,
                                                     SingleChoice, MultipleChoice,
                                                     DateTime, Year,
                                                     ListString, ListRelationship,
                                                     Geo, SingleRelationship, UniqueName,
                                                     AddressAutocode, GeoAutoCode,
                                                     SourceCountrySelection, ReverseRelationship, ReverseListRelationship)


from flaskinventory.users.constants import USER_ROLES
from flaskinventory.flaskdgraph import Schema
from flaskinventory.auxiliary import icu_codes

"""
    Entry
"""


class Entry(Schema):

    uid = UIDPredicate()
    
    unique_name = UniqueName()
    
    name = String(required=True)
    
    other_names = ListString(overwrite=True)
    
    entry_notes = String(description='Do you have any other notes on the entry that you just coded?',
                         large_textfield=True)
    
    wikidataID = Integer(label='WikiData ID',
                         overwrite=True,
                         new=False)
    
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
                             render_kw={'placeholder': 'Separate by comma'}, 
                             overwrite=True)
    
    is_person = Boolean(description='Is the media organisation a person?',
                        default=False)
    
    ownership_kind = SingleChoice(choices={
                                    'NA': "Don't know / NA",
                                    'public ownership': 'Mainly public ownership',
                                    'private ownership': 'Mainly private Ownership',
                                    'political party': 'Political Party',
                                    'unknown': 'Unknown Ownership'},
                                  description='Is the media organization mainly privately owned or publicly owned?')

    country = SingleRelationship(relationship_constraint='Country', 
                                 allow_new=False,
                                 overwrite=True, 
                                 description='In which country is the organisation located?')
    
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
                                    })
    
    address_string = AddressAutocode(new=False,
                                     render_kw={'placeholder': 'Main address of the organization.'})
    
    address_geo = GeoAutoCode(read_only=True, new=False, hidden=True)
    
    employees = String(description='How many employees does the news organization have?',
                       render_kw={
                           'placeholder': 'Most recent figure as plain number'},
                       new=False)
    
    founded = DateTime(new=False)


class Resource(Entry):

    description = String(large_textfield=True)
    authors = ListString(render_kw={'placeholder': 'Separate by comma'})
    published_date = DateTime()
    last_updated = DateTime()
    url = String()
    doi = String()
    arxiv = String()

class Archive(Resource):

    access = SingleChoice(choices={'free': 'Free',
                                    'restricted': 'Restricted'})
    sources_included = ListRelationship(relationship_constraint='Source', allow_new=False)
    fulltext = Boolean(description='Dataset contains fulltext')
    country = ListRelationship(relationship_constraint=['Country', 'Multinational'])


class Source(Entry):

    channel = SingleRelationship(description='Through which channel is the news source distributed?',
                                 edit=False,
                                 autoload_choices=True,
                                 relationship_constraint='Channel',
                                 read_only=True,
                                 required=True)

    name = String(label='Name of the News Source',
                  required=True,
                  description='What is the name of the news source?',
                  render_kw={'placeholder': "e.g. 'The Royal Gazette'"})
    
    other_names = ListString(description='Is the news source known by alternative names (e.g. Krone, Die Kronen Zeitung)?',
                             render_kw={'placeholder': 'Separate by comma'}, 
                             overwrite=True)

    founded = DateTime(description="What year was the print news source founded?")

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
                                        required=True)

    special_interest = Boolean(description='Does the news source have one main topical focus?',
                                label='Yes, is a special interest publication')
    
    topical_focus = MultipleChoice(description="What is the main topical focus of the news source?",
                                    choices={'politics': 'Politics', 
                                             'society': 'Society & Panorama', 
                                             'economy': 'Business, Economy, Finance & Stocks', 
                                             'religion': 'Religion', 
                                             'science': 'Science & Technology', 
                                             'media': 'Media', 
                                             'environment': 'Environment', 
                                             'education': 'Education'},
                                    tom_select=True)
    
    publication_cycle = SingleChoice(description="What is the publication cycle of the source?",
                                        choices={'continuous': 'Continuous', 
                                                 'daily': 'Daily (7 times a week)', 
                                                 'multiple times per week': 'Multiple times per week', 
                                                 'weekly': 'Weekly', 
                                                 'twice a month': 'Twice a month', 
                                                 'monthly': 'Monthly', 
                                                 'less than monthly': 'Less frequent than monthly', 
                                                 'NA': "Don't Know / NA"},
                                                 required=True)

    publication_cycle_weekday = MultipleChoice(description="Please indicate the specific day(s)",
                                                choices={1: 'Monday', 
                                                        2: 'Tuesday', 
                                                        3: 'Wednesday', 
                                                        4: 'Thursday', 
                                                        5: 'Friday', 
                                                        6: 'Saturday', 
                                                        7: 'Sunday', 
                                                        'NA': "Don't Know / NA"},
                                                tom_select=True)

    geographic_scope = SingleChoice(description="What is the geographic scope of the news source?",
                                    choices={'multinational': 'Multinational', 
                                             'national': 'National', 
                                             'subnational': 'Subnational', 
                                             'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True)

    country = SourceCountrySelection(label='Countries', 
                                        description='Which countries are in the geographic scope?',
                                        required=True)

    geographic_scope_subunit = ListRelationship(label='Subunits',
                                                description='What is the subnational scope?',
                                                relationship_constraint='Subunit',
                                                autoload_choices=True,
                                                overwrite=True,
                                                tom_select=True)

    languages = MultipleChoice(description="In which language(s) does the news source publish its news texts?",
                                required=True,
                                choices=icu_codes,
                                tom_select=True)

    payment_model = SingleChoice(description="Is the content produced by the news source accessible free of charge?",
                                    choices={'free': 'Free, all content is free of charge', 
                                            'partly free': 'Some content is free of charge', 
                                            'not free': 'No content is free of charge', 
                                            'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True)

    contains_ads = SingleChoice(description="Does the news source contain advertisements?",
                                    choices={'yes': 'Yes', 
                                                'no': 'No', 
                                                'non subscribers': 'Only for non-subscribers', 
                                                'NA': "Don't Know / NA"},
                                    required=True,
                                    radio_field=True)

    published_by = ReverseListRelationship('publishes', 
                                       label='Published by', 
                                       allow_new=True)

    included_in = ReverseListRelationship('sources_included', allow_new=False, label='News source included in these resources')


# entry_countries = ListRelationship(
#     'country', relationship_constraint='Country', allow_new=False, overwrite=True)


