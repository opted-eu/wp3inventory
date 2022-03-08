from flask_wtf import FlaskForm
from wtforms import SubmitField

from flaskinventory.users.constants import USER_ROLES

class Schema:

    # registry of all types and which predicates they have
    # Key = Dgraph Type (string), val = dict of predicates
    __types__ = {}

    # Registry of permissions for each type
    __perm_registry_new__ = {}
    __perm_registry_edit__ = {}

    # registry of all predicates and which types use them
    # Key = predicate (string), Val = list(Dgraph Type (string))
    __predicates__ = {}

    # registry of explicit reverse relationship that should generate a form field
    # key = predicate (string), val = dict of predicates
    __reverse_predicates__ = {}

    def __init_subclass__(cls) -> None:
        from .dgraph_types import Predicate, ReverseRelationship, MutualRelationship
        predicates = {key: getattr(cls, key) for key in cls.__dict__.keys() if isinstance(getattr(cls, key), (Predicate, MutualRelationship))}
        reverse_predicates = {key: getattr(cls, key) for key in cls.__dict__.keys() if isinstance(getattr(cls, key), ReverseRelationship)}
        # inherit predicates from parent classes
        for parent in cls.__bases__:
            if parent.__name__ != Schema.__name__:
                predicates.update({k: v for k, v in Schema.get_predicates(
                    parent.__name__).items() if k not in predicates.keys()})
                reverse_predicates.update({k: v for k, v in Schema.get_reverse_predicates(
                    parent.__name__).items() if k not in reverse_predicates.keys()})
        Schema.__types__[cls.__name__] = predicates
        Schema.__reverse_predicates__[cls.__name__] = reverse_predicates
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

    @classmethod
    def get_types(cls) -> list:
        return list(cls.__types__.keys())

    @classmethod
    def get_predicates(cls, _cls) -> dict:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        return cls.__types__[_cls]

    @classmethod
    def get_reverse_predicates(cls, _cls) -> dict:
        if not isinstance(_cls, str):
            _cls = _cls.__name__
        if _cls in cls.__reverse_predicates__.keys():
            return cls.__reverse_predicates__[_cls]
        else:
            return None

    @classmethod
    def predicates(cls) -> dict:
        return cls.__types__[cls.__name__]

    @classmethod
    def reverse_predicates(cls) -> dict:
        if cls.__name__ in cls.__reverse_predicates__:
            return cls.__reverse_predicates__[cls.__name__]
        else:
            return None

    @classmethod
    def predicate_names(cls) -> list:
        return list(cls.__types__[cls.__name__].keys())

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
    def generate_new_entry_form(cls, dgraph_type=None) -> FlaskForm:

        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
            if cls.get_reverse_predicates(dgraph_type):
                fields.update(cls.get_reverse_predicates(dgraph_type))
        else:
            fields = cls.predicates()
            if cls.reverse_predicates():
                fields.update(cls.reverse_predicates())

        class F(FlaskForm):

            submit = SubmitField(f'Add New {cls.__name__}')

            def get_field(self, field):
                return getattr(self, field)

        for k, v in fields.items():
            if v.new:
                setattr(F, k, v.wtf_field)

        return F()

    @classmethod
    def generate_edit_entry_form(cls, dgraph_type=None, entry_review_status='pending') -> FlaskForm:

        if dgraph_type:
            fields = cls.get_predicates(dgraph_type)
        else:
            fields = cls.predicates()

        if not isinstance(dgraph_type, str):
            dtype_label = dgraph_type.__name__
        else: dtype_label = dgraph_type

        class F(FlaskForm):

            submit = SubmitField(f'Edit this {dtype_label}')

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