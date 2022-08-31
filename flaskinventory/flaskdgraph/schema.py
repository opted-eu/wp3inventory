from copy import deepcopy
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms import IntegerField

from flaskinventory.users.constants import USER_ROLES


class Schema:

    # registry of all types and which predicates they have
    # Key = Dgraph Type (string), val = dict of predicates
    __types__ = {}

    # registry of all predicates and which types use them
    # Key = predicate (string), Val = list(Dgraph Type (string))
    __predicates_types__ = {}
    __reverse_predicates_types__ = {}

    __inheritance__ = {}

    # Registry of permissions for each type
    __perm_registry_new__ = {}
    __perm_registry_edit__ = {}

    # Registry of all predicates
    # key = Name of predicate (string), value = predicate (object)
    __predicates__ = {}

    # registry of all relationship predicates
    __relationship_predicates__ = {}

    # registry of explicit reverse relationship that should generate a form field
    # key = predicate (string), val = dict of predicates
    __reverse_relationship_predicates__ = {}

    # registry of all predicates that can be queried by users
    # have their attribute `queryable` set to `True`
    __queryable_predicates__ = {}

    __queryable_predicates_by_type__ = {}

    def __init_subclass__(cls) -> None:
        from .dgraph_types import _PrimitivePredicate, Facet, Predicate, SingleRelationship, ReverseRelationship, MutualRelationship
        predicates = {key: getattr(cls, key) for key in cls.__dict__ if isinstance(
            getattr(cls, key), (Predicate, MutualRelationship))}

        relationship_predicates = {key: getattr(cls, key) for key in cls.__dict__ if isinstance(
            getattr(cls, key), (SingleRelationship, MutualRelationship))}

        reverse_predicates = {key: getattr(cls, key) for key in cls.__dict__ if isinstance(
            getattr(cls, key), ReverseRelationship)}

        # base list of queryable predicates
        queryable_predicates = {key: val for key,
                                val in predicates.items() if val.queryable}
        # add reverse predicates that can be queried
        queryable_predicates.update(
            {val._predicate: val for key, val in reverse_predicates.items() if val.queryable})

        # inherit predicates from parent classes
        for parent in cls.__bases__:
            if parent.__name__ != Schema.__name__:
                predicates.update({k: v for k, v in Schema.get_predicates(
                    parent.__name__).items() if k not in predicates})
                relationship_predicates.update({k: v for k, v in Schema.get_relationships(
                    parent.__name__).items() if k not in predicates})
                reverse_predicates.update({k: v for k, v in Schema.get_reverse_predicates(
                    parent.__name__).items() if k not in reverse_predicates})

                # register inheritance
                if cls.__name__ not in Schema.__inheritance__:
                    Schema.__inheritance__[cls.__name__] = [parent.__name__]
                else:
                    Schema.__inheritance__[
                        cls.__name__].append(parent.__name__)
                if parent.__name__ in Schema.__inheritance__:
                    Schema.__inheritance__[
                        cls.__name__] += Schema.__inheritance__[parent.__name__]
                    Schema.__inheritance__[cls.__name__] = list(
                        set(Schema.__inheritance__[cls.__name__]))

        Schema.__types__[cls.__name__] = predicates
        Schema.__reverse_relationship_predicates__[
            cls.__name__] = reverse_predicates
        Schema.__perm_registry_new__[cls.__name__] = cls.__permission_new__
        Schema.__perm_registry_edit__[cls.__name__] = cls.__permission_edit__

        # Bind and "activate" predicates for initialized class
        for key in cls.__dict__:
            attribute = getattr(cls, key)
            if isinstance(attribute, (Predicate, MutualRelationship)):
                setattr(attribute, 'predicate', key)
                if attribute.facets:
                    for facet in attribute.facets.values():
                        facet.predicate = key
                        if facet.queryable:
                            queryable_predicates.update({str(facet): facet})
                if key not in cls.__predicates_types__:
                    cls.__predicates_types__.update({key: [cls.__name__]})
                else:
                    cls.__predicates_types__[key].append(cls.__name__)
                if isinstance(attribute, (SingleRelationship, MutualRelationship)):
                    if key not in cls.__relationship_predicates__:
                        cls.__relationship_predicates__.update(
                            {key: [cls.__name__]})
                    else:
                        cls.__relationship_predicates__[
                            key].append(cls.__name__)
                if key not in cls.__predicates__:
                    cls.__predicates__.update({key: attribute})
            elif isinstance(attribute, ReverseRelationship):
                if attribute.predicate not in cls.__reverse_predicates_types__:
                    cls.__reverse_predicates_types__.update(
                        {attribute.predicate: [cls.__name__]})
                else:
                    if cls.__name__ not in cls.__reverse_predicates_types__[attribute.predicate]:
                        cls.__reverse_predicates_types__[
                            attribute.predicate].append(cls.__name__)

        Schema.__queryable_predicates__.update(queryable_predicates)

        Schema.__queryable_predicates_by_type__[cls.__name__] = {
            key: val for key, val in predicates.items() if val.queryable}
        Schema.__queryable_predicates_by_type__[cls.__name__].update(
            {key: val for key, val in queryable_predicates.items() if isinstance(val, Facet)})
        Schema.__queryable_predicates_by_type__[cls.__name__].update(
            {val._predicate: val for key, val in reverse_predicates.items() if val.queryable})

    @classmethod
    def get_types(cls) -> list:
        """
            Get all types registered in the Schema.
            `Schema.get_types()` -> Returns a list of strings
        """
        return list(cls.__types__.keys())

    @classmethod
    def get_type(cls, dgraph_type: str) -> str:
        """
            Get the correct name of a DGraph Type
            Helpful when input is all lower case
            `Schema.get_type('fileformat')` -> 'FileFormat'
        """
        if not dgraph_type:
            return None
        assert isinstance(dgraph_type, str)
        for t in list(cls.__types__.keys()):
            if t.lower() == dgraph_type.lower():
                return t
        return None

    @classmethod
    def get_predicates(cls, _cls) -> dict:
        """
            Get all predicates of a DGraph Type
            Returns a dict of `{'predicate_name': <DGraph Predicate>}`
            `Schema.get_predicates('Source')` -> {'name': <DGraph Predicate "name"> ...}
        """
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        return deepcopy(cls.__types__[_cls])

    @classmethod
    def get_relationships(cls, _cls) -> dict:
        """
            Get all Relationships from the DGraph Type to other DGraph Types.
            Returns a dict of `{'predicate_name': <DGraph Predicate>}`
            `Schema.get_relationships('Source')` -> {'channel': <DGraph Predicate "channel"> ...}
        """
        from .dgraph_types import SingleRelationship, MutualRelationship
        if not isinstance(_cls, str):
            _cls = _cls.__name__

        relationships = cls.__types__[_cls]
        return {k: v for k, v in relationships.items() if isinstance(v, (SingleRelationship, MutualRelationship))}

    @classmethod
    def get_reverse_predicates(cls, _cls) -> dict:
        """
            Get all explicit reverse relationships from other DGraph Types to this DGraph Type.
            Returns a dict of `{'alias_reverse_predicate': <DGraph Predicate>}`
            `Schema.get_reverse_predicates('Source')` -> {'publishes_org': <DGraph Reverse Relationship "~publishes"> ...}
        """
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        if _cls in cls.__reverse_relationship_predicates__:
            return deepcopy(cls.__reverse_relationship_predicates__[_cls])
        else:
            return None

    @classmethod
    def predicates(cls) -> dict:
        """
            Get all predicates.
            If used on `Schema` get a complete dict of all registered predicates.
            If used on a class of a DGraph Type get a dict of all predicates for this type.
            Returns a dict of `{'predicate_name': <DGraph Predicate>}`
            `Schema.predicates()` -> Complete dict
            `FileFormat.predicates()` -> Only predicates for this DGraph Type
        """
        try:
            predicates = deepcopy(cls.__types__[cls.__name__])
        except KeyError:
            predicates = deepcopy(cls.__predicates__)

        return predicates

    @classmethod
    def relationship_predicates(cls) -> dict:
        return deepcopy(cls.__relationship_predicates__)

    @classmethod
    def reverse_predicates(cls) -> dict:
        if cls.__name__ in cls.__reverse_relationship_predicates__:
            return deepcopy(cls.__reverse_relationship_predicates__[cls.__name__])
        else:
            return None

    @classmethod
    def predicate_names(cls) -> list:
        try:
            predicates = list(cls.__types__[cls.__name__].keys())
        except KeyError:
            predicates = list(cls.__predicates__.keys())

        return predicates

    @classmethod
    def resolve_inheritance(cls, _cls) -> list:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        assert _cls in cls.__types__, f'DGraph Type "{_cls}" not found!'
        dgraph_types = [_cls]
        if _cls in cls.__inheritance__:
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

    @classmethod
    def get_queryable_predicates(cls, _cls=None) -> dict:
        if _cls is None:
            try:
                return deepcopy(cls.__queryable_predicates_by_type__[cls.__name__])
            except KeyError:
                return deepcopy(cls.__queryable_predicates__)

        if not isinstance(_cls, str):
            _cls = _cls.__name__
        else:
            _cls = cls.get_type(_cls)

        try:
            return deepcopy(cls.__queryable_predicates_by_type__[_cls])
        except KeyError:
            return {}

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
    def generate_edit_entry_form(cls, dgraph_type=None,
                                 populate_obj: dict = None,
                                 entry_review_status='pending',
                                 skip_fields: list = None) -> FlaskForm:

        from .dgraph_types import SingleRelationship, ReverseRelationship, MutualRelationship

        if populate_obj is None:
            populate_obj = {}

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
