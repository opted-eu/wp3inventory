from flaskinventory.flaskdgraph.dgraph_types import (String, Integer, Boolean, UIDPredicate,
                                                     SingleChoice, DateTime,
                                                     ListString, ListRelationship,
                                                     Geo, SingleRelationship, UniqueName,
                                                     AddressAutocode, GeoAutoCode)
from flask_wtf import FlaskForm
from wtforms import SubmitField

from flaskinventory.users.constants import USER_ROLES

class Schema:

    _types = {}

    def __init_subclass__(cls) -> None:
        predicates = {key: getattr(cls, key) for key in cls.__dict__.keys() if hasattr(getattr(cls, key), 'predicate')}
        # inherit predicates from parent classes
        for parent in cls.__bases__:
            if parent.__name__ != Schema.__name__:
                predicates.update({k: v for k, v in Schema.get_predicates(parent.__name__).items() if k not in predicates.keys()})
        Schema._types[cls.__name__] = predicates
        for predicate in cls.__dict__.keys():
            if not predicate.startswith('__'):
                setattr(getattr(cls, predicate), 'predicate', predicate)

    @classmethod
    def get_types(cls):
        return list(cls._types.keys())
    
    @classmethod
    def get_predicates(cls, _cls):
        if isinstance(_cls, Schema):
            _cls = _cls.__name__
        return cls._types[_cls]
    
    @classmethod
    def predicates(cls):
        return cls._types[cls.__name__]

    @classmethod
    def predicate_names(cls):
        return list(cls._types[cls.__name__].keys())

    @classmethod
    def generate_new_entry_form(cls, dgraph_type=None):
        
        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
        else:
            fields = cls.predicates()

        class F(FlaskForm):

            submit = SubmitField(f'Add New {cls.__name__}')

            def get_field(self, field):
                return getattr(self, field)
            
        for k, v in fields.items():
            if v.new:
                setattr(F, k, v.wtf_field)

        return F()

    @classmethod
    def generate_edit_entry_form(cls, dgraph_type=None, entry_review_status='pending'):
        
        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
        else:
            fields = cls.predicates()

        class F(FlaskForm):

            submit = SubmitField(f'Edit this {cls.__name__}')

            def get_field(self, field):
                try:
                    return getattr(self, field)
                except AttributeError:
                    return None

        from flask_login import current_user
            
        for k, v in fields.items():
            if v.edit and current_user.user_role >= v.permission:
                setattr(F, k, v.wtf_field)

        
        if current_user.user_role >= USER_ROLES.Reviewer and entry_review_status == 'pending':
            setattr(F, "accept", SubmitField('Edit and Accept'))

        return F()



"""
    Entry
"""

class Entry(Schema):

    """
        Now we only need a way to distinguish which predicates are visible in different views
        some only for 'add', others for 'edit'
    """

    uid = UIDPredicate()
    unique_name = UniqueName(required=True, new=False, permission=USER_ROLES.Reviewer)
    name = String(required=True)
    other_names = ListString(overwrite=True)
    entry_notes = String(description='Do you have any other notes on the entry that you just coded?', large_textfield=True)
    wikidataID = Integer(overwrite=True, label='WikiData ID', new=False)
    entry_review_status = SingleChoice(choices={'draft': 'Draft',
                                            'pending': 'Pending',
                                            'accepted': 'Accepted',
                                            'rejected': 'Rejected'},
                                        default='pending',
                                        required=True, 
                                        new=False,
                                        permission=USER_ROLES.Reviewer)
        

class Organization(Entry):

    name = String(label='Organization Name', required=True, description='What is the legal or official name of the media organisation?')
    other_names = ListString(description='Does the organisation have any other names or common abbreviations?',
                            render_kw={'placeholder': 'Separate by comma'}, overwrite=True)
    is_person = Boolean(default=False, description='Is the media organisation a person?')
    ownership_kind = SingleChoice(choices={
                                  'NA': "Don't know / NA",
                                  'public ownership': 'Mainly public ownership',
                                  'private ownership': 'Mainly private Ownership',
                                  'political party': 'Political Party',
                                  'unknown': 'Unknown Ownership'},
                                description='Is the media organization mainly privately owned or publicly owned?')

    country = SingleRelationship(relationship_constraint='Country', allow_new=False, overwrite=True, description='In which country is the organisation located?')
    publishes = ListRelationship(allow_new=False, relationship_constraint='Source', overwrite=True, description= 'Which news sources publishes the organisation (or person)?',
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
    address_string = AddressAutocode(new=False)
    address_geo = GeoAutoCode(read_only=True, new=False)
    employees = String(description='How many employees does the news organization have?',
                        render_kw={'placeholder': 'Most recent figure as plain number'},
                        new=False)
    founded = DateTime(new=False)



# entry_countries = ListRelationship(
#     'country', relationship_constraint='Country', allow_new=False, overwrite=True)