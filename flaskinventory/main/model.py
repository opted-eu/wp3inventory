from inspect import ismethod
from flaskinventory.flaskdgraph.dgraph_types import (String, Integer, Boolean,
                                                     SingleChoice, DateTime,
                                                     ListString, ListRelationship,
                                                     Geo, SingleRelationship, UniqueName,
                                                     AddressAutocode, GeoAutoCode)


class Schema:

    _types = {}

    def __init_subclass__(cls) -> None:
        predicates = [cls.__getattribute__(cls, field) for field in cls.__dict__.keys() if not field.startswith('_')]
        Schema._types[cls.__name__] = predicates

    @classmethod
    def get_types(cls):
        return list(cls._types.keys())
    
    @classmethod
    def get_predicates(cls, _cls):
        if isinstance(_cls, Schema):
            _cls = _cls.__name__
        return cls._types[_cls]


"""
    Entry
"""

class Entry(Schema):

    """
        Now we only need a way to distinguish which predicates are visible in different views
        some only for 'add', others for 'edit'
    """

    uid = String('uid', render_kw={'readonly': True})
    unique_name = UniqueName('unique_name', required=True)
    entry_name = String('name', required=True)
    other_names = ListString('other_names', overwrite=True)
    entry_notes = String('entry_notes', description='Do you have any other notes on the entry that you just coded?', large_textfield=True)
    wikidataID = Integer('wikidataID', overwrite=True, label='WikiData ID')
    entry_review_status = SingleChoice('entry_review_status',
                                    choices={'draft': 'Draft',
                                            'pending': 'Pending',
                                            'accepted': 'Accepted',
                                            'rejected': 'Rejected'},
                                    default='pending',
                                    required=True)
    
uid = String('uid', render_kw={'readonly': True})
unique_name = UniqueName('unique_name', required=True)
entry_name = String('name', required=True)
other_names = ListString('other_names', overwrite=True)
entry_notes = String('entry_notes', description='Do you have any other notes on the entry that you just coded?', large_textfield=True)
wikidataID = Integer('wikidataID', overwrite=True, label='WikiData ID')
entry_review_status = SingleChoice('entry_review_status',
                                choices={'draft': 'Draft',
                                        'pending': 'Pending',
                                        'accepted': 'Accepted',
                                        'rejected': 'Rejected'},
                                default='pending',
                                required=True)

entry_fields = [unique_name, entry_name, other_names, entry_notes, wikidataID, entry_review_status]

"""
    Organization
"""

class Organization(Entry):

    entry_name = String('name', label='Organization Name', required=True, description='What is the legal or official name of the media organisation?')
    other_names = String('other_names', description='Does the organisation have any other names or common abbreviations?',
            render_kw={'placeholder': 'Separate by comma'})
    is_person = Boolean('is_person', default=False, description='Is the media organisation a person?')
    ownership_kind = SingleChoice('ownership_kind',
                              choices={
                                  'NA': "Don't know / NA",
                                  'public ownership': 'Mainly public ownership',
                                  'private ownership': 'Mainly private Ownership',
                                  'political party': 'Political Party',
                                  'unknown': 'Unknown Ownership'},
                                description='Is the media organization mainly privately owned or publicly owned?')

    organization_country = SingleRelationship(
        'country', relationship_constraint='Country', allow_new=False, overwrite=True, description='In which country is the organisation located?')
    publishes = ListRelationship(
        'publishes', allow_new=False, relationship_constraint='Source', overwrite=True, description= 'Which news sources publishes the organisation (or person)?',
                render_kw={'placeholder': 'Type to search existing news sources and add multiple...'})
    owns = ListRelationship('owns', allow_new=False,
                            relationship_constraint='Organization', 
                            overwrite=True, 
                            description='Which other media organisations are owned by this new organisation (or person)?',
                            render_kw={'placeholder': 'Type to search existing organisations and add multiple...'})

    party_affiliated = SingleChoice('party_affiliated',
                                    choices={
                                        'NA': "Don't know / NA",
                                        'yes': 'Yes',
                                        'no': 'No'
                                    })
    address_string = AddressAutocode('address_string')
    address_geo = GeoAutoCode('address_geo')
    employees = String('employees', description='How many employees does the news organization have?',
                render_kw={'placeholder': 'Most recent figure as plain number'})
    founded = DateTime('founded')


organization_name = String('name', label='Organization Name', required=True, description='What is the legal or official name of the media organisation?')
organization_other_names = String('other_names', description='Does the organisation have any other names or common abbreviations?',
            render_kw={'placeholder': 'Separate by comma'})
is_person = Boolean('is_person', default=False, description='Is the media organisation a person?')
ownership_kind = SingleChoice('ownership_kind',
                              choices={
                                  'NA': "Don't know / NA",
                                  'public ownership': 'Mainly public ownership',
                                  'private ownership': 'Mainly private Ownership',
                                  'political party': 'Political Party',
                                  'unknown': 'Unknown Ownership'},
                                description='Is the media organization mainly privately owned or publicly owned?')

organization_country = SingleRelationship(
    'country', relationship_constraint='Country', allow_new=False, overwrite=True, description='In which country is the organisation located?')
publishes = ListRelationship(
    'publishes', allow_new=False, relationship_constraint='Source', overwrite=True, description= 'Which news sources publishes the organisation (or person)?',
            render_kw={'placeholder': 'Type to search existing news sources and add multiple...'})
owns = ListRelationship('owns', allow_new=False,
                        relationship_constraint='Organization', 
                        overwrite=True, 
                        description='Which other media organisations are owned by this new organisation (or person)?',
                        render_kw={'placeholder': 'Type to search existing organisations and add multiple...'})

party_affiliated = SingleChoice('party_affiliated',
                                choices={
                                    'NA': "Don't know / NA",
                                    'yes': 'Yes',
                                    'no': 'No'
                                })
address_string = AddressAutocode('address_string')
address_geo = GeoAutoCode('address_geo')
employees = String('employees', description='How many employees does the news organization have?',
            render_kw={'placeholder': 'Most recent figure as plain number'})
founded = DateTime('founded')

organization_fields = [ownership_kind, is_person, party_affiliated, organization_country, address_string, address_geo, employees, founded, owns, publishes]


entry_countries = ListRelationship(
    'country', relationship_constraint='Country', allow_new=False, overwrite=True)