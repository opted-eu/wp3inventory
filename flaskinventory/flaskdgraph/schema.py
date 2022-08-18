from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms import IntegerField

from flaskinventory.users.constants import USER_ROLES


class Schema:

    # registry of all types and which predicates they have
    # Key = Dgraph Type (string), val = dict of predicates
    __types__ = {}

    __inheritance__ = {}

    # Registry of permissions for each type
    __perm_registry_new__ = {}
    __perm_registry_edit__ = {}

    # registry of all predicates and which types use them
    # Key = predicate (string), Val = list(Dgraph Type (string))
    __predicates__ = {}

    # registry of all relationship predicates
    __relationship_predicates__ = {}

    # registry of explicit reverse relationship that should generate a form field
    # key = predicate (string), val = dict of predicates
    __reverse_relationship_predicates__ = {}

    def __init_subclass__(cls) -> None:
        from .dgraph_types import Predicate, SingleRelationship, ReverseRelationship, MutualRelationship
        predicates = {key: getattr(cls, key) for key in cls.__dict__.keys(
        ) if isinstance(getattr(cls, key), (Predicate, MutualRelationship))}
        relationship_predicates = {key: getattr(cls, key) for key in cls.__dict__.keys(
        ) if isinstance(getattr(cls, key), (SingleRelationship, MutualRelationship))}
        reverse_predicates = {key: getattr(cls, key) for key in cls.__dict__.keys(
        ) if isinstance(getattr(cls, key), ReverseRelationship)}

        # inherit predicates from parent classes
        for parent in cls.__bases__:
            if parent.__name__ != Schema.__name__:
                predicates.update({k: v for k, v in Schema.get_predicates(
                    parent.__name__).items() if k not in predicates.keys()})
                relationship_predicates.update({k: v for k, v in Schema.get_relationships(
                    parent.__name__).items() if k not in predicates.keys()})
                reverse_predicates.update({k: v for k, v in Schema.get_reverse_predicates(
                    parent.__name__).items() if k not in reverse_predicates.keys()})

                # register inheritance
                if cls.__name__ not in Schema.__inheritance__.keys():
                    Schema.__inheritance__[cls.__name__] = [parent.__name__]
                else:
                    Schema.__inheritance__[
                        cls.__name__].append(parent.__name__)
                if parent.__name__ in Schema.__inheritance__.keys():
                    Schema.__inheritance__[
                        cls.__name__] += Schema.__inheritance__[parent.__name__]
                    Schema.__inheritance__[cls.__name__] = list(
                        set(Schema.__inheritance__[cls.__name__]))

        Schema.__types__[cls.__name__] = predicates
        Schema.__reverse_relationship_predicates__[
            cls.__name__] = reverse_predicates
        Schema.__perm_registry_new__[cls.__name__] = cls.__permission_new__
        Schema.__perm_registry_edit__[cls.__name__] = cls.__permission_edit__
        for key in cls.__dict__.keys():
            attribute = getattr(cls, key)
            if isinstance(attribute, (Predicate, MutualRelationship)):
                setattr(attribute, 'predicate', key)
                if key not in cls.__predicates__.keys():
                    cls.__predicates__.update({key: [cls.__name__]})
                else:
                    cls.__predicates__[key].append(cls.__name__)
                if isinstance(attribute, (SingleRelationship, MutualRelationship)):
                    if key not in cls.__relationship_predicates__.keys():
                        cls.__relationship_predicates__.update(
                            {key: [cls.__name__]})
                    else:
                        cls.__relationship_predicates__[
                            key].append(cls.__name__)

    @classmethod
    def get_types(cls) -> list:
        return list(cls.__types__.keys())

    @classmethod
    def get_type(cls, dgraph_type: str) -> str:
        # get the correct name of a dgraph type
        # helpful when input is all lower case
        assert isinstance(dgraph_type, str)
        for t in list(cls.__types__.keys()):
            if t.lower() == dgraph_type.lower():
                return t
        return None

    @classmethod
    def get_predicates(cls, _cls) -> dict:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        return cls.__types__[_cls]

    @classmethod
    def get_relationships(cls, _cls) -> dict:
        from .dgraph_types import SingleRelationship, MutualRelationship
        if not isinstance(_cls, str):
            _cls = _cls.__name__

        relationships = cls.__types__[_cls]
        return {k: v for k, v in relationships.items() if isinstance(v, (SingleRelationship, MutualRelationship))}

    @classmethod
    def get_reverse_predicates(cls, _cls) -> dict:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        if _cls in cls.__reverse_relationship_predicates__.keys():
            return cls.__reverse_relationship_predicates__[_cls]
        else:
            return None

    @classmethod
    def predicates(cls) -> dict:
        return cls.__types__[cls.__name__]

    @classmethod
    def relationship_predicates(cls) -> dict:
        return cls.__relationship_predicates__

    @classmethod
    def reverse_predicates(cls) -> dict:
        if cls.__name__ in cls.__reverse_relationship_predicates__:
            return cls.__reverse_relationship_predicates__[cls.__name__]
        else:
            return None

    @classmethod
    def predicate_names(cls) -> list:
        return list(cls.__types__[cls.__name__].keys())

    @classmethod
    def resolve_inheritance(cls, _cls) -> list:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        assert _cls in cls.__types__.keys(), f'DGraph Type "{_cls}" not found!'
        dgraph_types = [_cls]
        if _cls in cls.__inheritance__.keys():
            dgraph_types += cls.__inheritance__[_cls]
        return dgraph_types

    @classmethod
    def permissions_new(cls, _cls) -> int:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        return cls.__perm_registry_new__[_cls]

    @classmethod
    def permissions_edit(cls, _cls) -> int:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        return cls.__perm_registry_edit__[_cls]

    @staticmethod
    def populate_form(form: FlaskForm, populate_obj: dict, fields: dict) -> FlaskForm:
        from flaskinventory.flaskdgraph.dgraph_types import SingleChoice

        for k, value in populate_obj.items():
            if hasattr(form, k):
                if type(value) is dict:
                    if 'uid' in value.keys():
                        value = value['uid']
                elif type(value) is list and not isinstance(fields[k], SingleChoice):
                    if type(value[0]) is str:
                        delimiter = getattr(fields[k], 'delimiter', ',')
                        value = delimiter.join(value)
                    elif type(value[0]) is int:
                        value = [str(val) for val in value]
                    elif 'uid' in value[0].keys():
                        value = [subval['uid'] for subval in value]
                        if len(value) == 1:
                            value = value[0]
                if isinstance(getattr(form, k), IntegerField) and isinstance(value, datetime):
                    # cast datetime as year if field does not need to be too specific
                    value = value.year
                setattr(getattr(form, k), 'data', value)
        return form

    @classmethod
    def generate_new_entry_form(cls, dgraph_type=None, populate_obj: dict = None) -> FlaskForm:

        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
            if cls.get_reverse_predicates(dgraph_type):
                fields.update(cls.get_reverse_predicates(dgraph_type))
        else:
            fields = cls.predicates()
            if cls.reverse_predicates():
                fields.update(cls.reverse_predicates())

        if not isinstance(dgraph_type, str):
            submit_label = dgraph_type.__name__
        else:
            submit_label = dgraph_type

        class F(FlaskForm):

            submit = SubmitField(f'Add New {submit_label}')

            def get_field(self, field):
                return getattr(self, field)

        for k, v in fields.items():
            if v.new:
                setattr(F, k, v.wtf_field)

        form = F()
        # ability to pre-populate the form with data
        if populate_obj:
            form = cls.populate_form(form, populate_obj, fields)

        return form

    @classmethod
    def generate_edit_entry_form(cls, dgraph_type=None, populate_obj: dict = {}, entry_review_status='pending', skip_fields: list = None) -> FlaskForm:

        from .dgraph_types import SingleRelationship, ReverseRelationship, MutualRelationship

        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
        else:
            fields = cls.predicates()

        if not isinstance(dgraph_type, str):
            dtype_label = dgraph_type.__name__
        else:
            dtype_label = dgraph_type

        class F(FlaskForm):

            submit = SubmitField(f'Edit this {dtype_label}')

            def get_field(self, field):
                try:
                    return getattr(self, field)
                except AttributeError:
                    return None

        from flask_login import current_user

        # FlaskForm Factory
        # Add fields depending on DGraph Type
        skip_fields = skip_fields or []
        for k, v in fields.items():
            # Allow to manually filter out some fields / hide them from users
            if k in skip_fields:
                continue
            if v.edit and current_user.user_role >= v.permission:
                if isinstance(v, (SingleRelationship, ReverseRelationship, MutualRelationship)) and k in populate_obj.keys():
                    if not v.autoload_choices:
                        choices = [(subval['uid'], subval['name'])
                                   for subval in populate_obj[k]]
                        v.choices_tuples = choices
                setattr(F, k, v.wtf_field)

        if current_user.user_role >= USER_ROLES.Reviewer and entry_review_status == 'pending':
            setattr(F, "accept", SubmitField('Edit and Accept'))

        # Instatiate the form from the factory
        form = F()

        # Populate instance with existing values
        form = cls.populate_form(form, populate_obj, fields)

        return form
