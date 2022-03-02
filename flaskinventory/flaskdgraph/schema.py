from flask_wtf import FlaskForm
from wtforms import SubmitField

from flaskinventory.users.constants import USER_ROLES

class Schema:

    _types = {}

    def __init_subclass__(cls) -> None:
        predicates = {key: getattr(cls, key) for key in cls.__dict__.keys(
        ) if hasattr(getattr(cls, key), 'predicate')}
        # inherit predicates from parent classes
        for parent in cls.__bases__:
            if parent.__name__ != Schema.__name__:
                predicates.update({k: v for k, v in Schema.get_predicates(
                    parent.__name__).items() if k not in predicates.keys()})
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