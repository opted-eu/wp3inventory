""" 
    Classes to represent DGraph objects in Python
    These are helper classes to automatically generate
    nquad statements from dictionaries
    May later be used for automatic query building
"""

from typing import Union, Any
import datetime
import json

# external utils
from slugify import slugify
import secrets
from dateutil import parser as dateparser


from flaskinventory import dgraph

from .schema import Schema
from .customformfields import NullableDateField, TomSelectField, TomSelectMutlitpleField
from .utils import validate_uid, strip_query

from flaskinventory.errors import InventoryPermissionError, InventoryValidationError
from flaskinventory.add.external import geocode, reverse_geocode
from flaskinventory.users.constants import USER_ROLES

from wtforms import (StringField, SelectField, SelectMultipleField,
                     DateField, BooleanField, TextAreaField, RadioField, IntegerField)
from wtforms.validators import DataRequired, Optional


"""
    DGraph Primitives
"""


class UID:

    def __init__(self, uid, facets=None):
        self.uid = uid.strip()
        self.facets = facets

    def __str__(self) -> str:
        return f'{self.uid}'

    def __repr__(self) -> str:
        return f'<{self.uid}>'

    def update_facets(self, facets: dict) -> None:
        if self.facets:
            self.facets.update(facets)
        else:
            self.facets = facets

    @property
    def nquad(self) -> str:
        return f'<{self.uid}>'

    @property
    def query(self) -> str:
        return f'{self.uid}'


class NewID:

    def __init__(self, newid, facets=None, suffix=None):
        if newid.startswith('_:'):
            self.newid = newid.strip()
        else:
            self.newid = f'_:{slugify(newid, separator="_")}'

        if suffix:
            self.newid += f'_{suffix}'
        else:
            self.newid += secrets.token_urlsafe(4)

        self.facets = facets

        self.original_value = newid.strip()

    def __str__(self) -> str:
        return self.newid

    def __repr__(self) -> str:
        return f'{self.newid}'

    def update_facets(self, facets: dict) -> None:
        if self.facets:
            self.facets.update(facets)
        else:
            self.facets = facets

    @property
    def nquad(self) -> str:
        return f'{self.newid}'


class _PrimitivePredicate:

    """
        Private Class to resolve inheritance conflicts
        Base class for constructing Predicate Classes
    """

    dgraph_predicate_type = 'string'
    is_list_predicate = False
    comparison_operator = "eq"

    def __init__(self,
                 label: str = None,
                 default: str = None,
                 required=False,
                 overwrite=False,
                 new=True,
                 edit=True,
                 queryable=False,
                 permission=USER_ROLES.Contributor,
                 read_only=False,
                 hidden=False,
                 description='',
                 tom_select=False,
                 render_kw: dict = None,
                 predicate_alias: list = None,
                 comparison_operator: str = None) -> None:
        """
            Contruct a new Primitive Predicate
        """

        self.predicate = None
        self._label = label
        self.read_only = read_only
        self.hidden = hidden
        self.new = new
        self.edit = edit
        self.queryable = queryable
        self.permission = permission
        if comparison_operator:
            self.comparison_operator = comparison_operator

        # WTF Forms
        self.required = required
        self.form_description = description
        self.tom_select = tom_select
        self.render_kw = render_kw or {}

        if hidden:
            self.render_kw.update(hidden=hidden)

        if read_only:
            self.render_kw.update(readonly=read_only)

        # default value applied when nothing is specified
        if isinstance(default, (Scalar, UID, NewID, list, tuple, set)) or default is None:
            self._default = default
        else:
            self._default = Scalar(default)

        # delete all values first before writing new ones
        self.overwrite = overwrite

        # other references to this predicate (might delete later)
        self.predicate_alias = predicate_alias


    def __str__(self) -> str:
        return f'{self.predicate}'

    def __repr__(self) -> str:
        if self.predicate:
            return f'<Primitive "{self.predicate}">'
        else:
            return f'<Unbound Primitive>'

    @classmethod
    def from_key(cls, key):
        cls_ = cls()
        cls_.predicate = key
        return cls_

    @property
    def default(self):
        return self._default

    @property
    def label(self):
        if self._label:
            return self._label
        else:
            return self.predicate.replace('_', ' ').title()

    @property
    def nquad(self) -> str:
        if self.predicate == '*':
            return '*'
        else:
            return f'<{self.predicate}>'

    @property
    def query(self) -> str:
        return f'{self.predicate}'

    def validation_hook(self, data):
        # this method is called in validation by default
        # when custom validation is required, overwriting this hook
        # is the preferred way.
        return data

    def validate(self, data, facets=None, **kwargs):
        # Validation method that is called by data sanitizer
        # When overwriting this method make sure to accept
        # `facets` as keyword argument
        # preferably this method should return a Scalar object
        data = self.validation_hook(data)
        if isinstance(data, (list, set, tuple)):
            return [Scalar(item, facets=facets) if isinstance(item, (str, int, datetime.datetime, datetime.date)) else item for item in data]
        elif isinstance(data, (str, int, datetime.datetime, datetime.date)):
            return Scalar(data, facets=facets)
        else:
            return data

    def query_filter(self, vals: Union[str, list], **kwargs) -> str:

        if vals is None:
            return f'has({self.predicate})'

        if not isinstance(vals, list):
            vals = [vals]

        if self.is_list_predicate:
            return " AND ".join([f'{self.comparison_operator}({self.predicate}, "{strip_query(val)}")' for val in vals])
        else:
            if not 'uid' in self.dgraph_predicate_type:
                vals_string = ", ".join([f'"{strip_query(val)}"' for val in vals])
            else:
                vals_string = ", ".join(
                    [f'{validate_uid(val)}' for val in vals if validate_uid(val)])
            if len(vals) == 1:
                return f'{self.comparison_operator}({self.predicate}, {vals_string})'
            else:
                return f'{self.comparison_operator}({self.predicate}, [{vals_string}])'

    def _prepare_query_field(self):
        # not a very elegant solution...
        # provides a hook for UI (JavaScript)
        if self.predicate:
            self.render_kw.update({'data-entities': ",".join(Schema.__predicates_types__[self.predicate])})

    @property
    def query_field(self) -> StringField:
        self._prepare_query_field()
        return StringField(label=self.label, render_kw=self.render_kw)



class Predicate(_PrimitivePredicate):

    """
        Base Class for representing DGraph Predicates
        Is used for validating data, generating DGraph queries & mutations,
        and also provides generators for WTF Form Fields

    """


    def __init__(self, large_textfield=False, *args, **kwargs) -> None:
        """
            Contruct a new predicate

            :param label:
                User facing label for predicate, 
                default: automatically generated from 'predicate'
            :param default:
                Default value when validating when nothing is specified
            :param overwrite:
                delete all values first before writing new ones.
            :param new:
                show this predicate when a new entry is made.
            :param edit:
                show this predicate when entry is edited.
            :param read_only:
                if 'True' users cannot edit this field.
            :param hidden:
                if 'True' form field will be hidden from users.
            :param required:
                Sets required flag for generated WTF Field.
            :param description:
                Passes description to WTF Field.
            :param tom_select:
                Instantiate TomSelect classes for WTF Fields.
            :param large_textfield:
                If true renders a TextAreaField
        """

        super().__init__(*args, **kwargs)

        self.large_textfield = large_textfield


    def __str__(self) -> str:
        return f'{self.predicate}'

    def __repr__(self) -> str:
        if self.predicate:
            return f'<DGraph Predicate "{self.predicate}">'
        else:
            return f'<Unbound DGraph Predicate>'

    @property
    def wtf_field(self) -> StringField:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        if self.large_textfield:
            return TextAreaField(label=self.label, validators=validators, description=self.form_description, render_kw=self.render_kw)
        return StringField(label=self.label, validators=validators, description=self.form_description, render_kw=self.render_kw)


class Scalar:

    """
        Utility class for 
    """

    def __init__(self, value, facets=None):
        if type(value) in [datetime.date, datetime.datetime]:
            self.year = value.year
            self.month = value.month
            self.day = value.day
            value = value.isoformat()
        elif type(value) is bool:
            value = str(value).lower()

        self.value = str(value).strip()
        if self.value != '*':
            self.value = json.dumps(self.value)
        self.facets = facets

    def __str__(self) -> str:
        if self.value != '*':
            return json.loads(self.value)
        else:
            return self.value

    def __repr__(self) -> str:
        if self.facets:
            return f'{self.value} ({self.facets})'
        return f'{self.value}'

    def update_facets(self, facets: dict) -> None:
        if self.facets:
            self.facets.update(facets)
        else:
            self.facets = facets

    @property
    def nquad(self) -> str:
        if self.value == '*':
            return '*'
        else:
            return f'''{self.value}'''


class GeoScalar(Scalar):

    """
        DGraph uses the convention of Lon, Lat
        Currently only supports Point Locations
    """

    def __init__(self, geotype, coordinates, facets=None):
        self.geotype = geotype
        if isinstance(coordinates, (list, tuple)):
            assert len(coordinates) == 2, 'Coordinates are not a pair!'
            self.coordinates = [round(c, 12) for c in coordinates]
            self.lon, self.lat = coordinates
        elif isinstance(coordinates, dict):
            assert 'lat' in coordinates and 'lon' in coordinates, 'Coordinates malformed'
            self.coordinates = [round(coordinates.get(
                'lat'), 12), round(coordinates.get('lon'), 12)]
            self.lat = coordinates.get('lat')
            self.lon = coordinates.get('lon')
        self.value = {'type': geotype, 'coordinates': coordinates}
        self.facets = facets

    def __str__(self) -> str:
        return str(self.value)

    @property
    def nquad(self) -> str:
        return '"' + str(self.value) + '"^^<geo:geojson>'


class Variable:

    """ Represents DGraph Query Variable """

    def __init__(self, var, predicate, val=False):
        self.var = var
        self.predicate = predicate
        self.val = val

    def __str__(self) -> str:
        return f'{self.var}'

    def __repr__(self) -> str:
        return f'{self.var} as {self.predicate}'

    @property
    def nquad(self) -> str:
        if self.val:
            return f'val({self.var})'
        else:
            return f'uid({self.var})'

    @property
    def query(self) -> str:
        return f'{self.var} as {self.predicate}'


class ReverseRelationship(_PrimitivePredicate):

    """
        default_predicates: dict with additional predicates that should be assigned to new entries
    """

    dgraph_predicate_type = 'uid'
    comparison_operator = 'uid_in'

    def __init__(self,
                 predicate_name,
                 allow_new=False,
                 autoload_choices=True,
                 relationship_constraint=None,
                 overwrite=False,
                 default_predicates=None,
                 *args, **kwargs) -> None:

        super().__init__(overwrite=overwrite, *args, **kwargs)

        if isinstance(relationship_constraint, str):
            relationship_constraint = [relationship_constraint]
        self.relationship_constraint = relationship_constraint
        self._predicate = f'~{predicate_name}'
        self._target_predicate = predicate_name
        self.predicate = predicate_name
        self.allow_new = allow_new

        self.default_predicates = default_predicates

        # WTForms
        # if we want the form field to show all choices automatically.
        self.autoload_choices = autoload_choices
        self.choices = {}
        self.choices_tuples = []
        self.entry_uid = None

    def __str__(self) -> str:
        return f'{self._predicate}'

    def __repr__(self) -> str:
        if self._predicate:
            return f'<DGraph Reverse Relationship "{self._predicate}">'
        else:
            return f'<Unbound DGraph Reverse Relationship>'

    def validate(self, data, node, facets=None) -> Union[UID, NewID, dict]:
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! Adding new items is not allowed, the provided value is not a UID: {data}')
            d = {'uid': NewID(data, facets=facets, suffix="_".join(self.relationship_constraint)) if self.relationship_constraint else NewID(data, facets=facets),
                 self._target_predicate: node}
            if self.relationship_constraint:
                d.update({'dgraph.type': self.relationship_constraint})
            return d
        d = {'uid': UID(uid, facets=facets), self._target_predicate: node}
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type not in self.relationship_constraint:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! UID specified does not match constraint, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')
        return d

    def get_choices(self):
        assert self.relationship_constraint

        query_string = '{ '

        for dgraph_type in self.relationship_constraint:
            query_string += f'''{dgraph_type.lower()}(func: type("{dgraph_type}"), orderasc: name) {{ uid name unique_name }} '''

        query_string += '}'

        choices = dgraph.query(query_string=query_string)

        if len(self.relationship_constraint) == 1:
            self.choices = {c['uid']: c['name']
                            for c in choices[self.relationship_constraint[0].lower()]}
            self.choices_tuples = [
                (c['uid'], c['name']) for c in choices[self.relationship_constraint[0].lower()]]

        else:
            self.choices = {}
            self.choices_tuples = {}
            for dgraph_type in self.relationship_constraint:
                self.choices_tuples[dgraph_type] = [
                    (c['uid'], c['name']) for c in choices[dgraph_type.lower()]]
                self.choices.update({c['uid']: c['name']
                                     for c in choices[dgraph_type.lower()]})

    @property
    def wtf_field(self) -> TomSelectField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        return TomSelectField(label=self.label, description=self.form_description, choices=self.choices_tuples, render_kw=self.render_kw)


class ReverseListRelationship(ReverseRelationship):

    is_list_predicate = True

    def validate(self, data, node, facets=None) -> Union[UID, NewID, dict]:
        if isinstance(data, str):
            data = data.split(',')

        data = set([item.strip() for item in data])
        uids = []

        for item in data:
            uid = super().validate(item, node, facets=facets)
            uids.append(uid)

        return uids

    def get_choices(self):
        assert self.relationship_constraint

        query_string = '{ '

        for dgraph_type in self.relationship_constraint:
            query_string += f'''{dgraph_type.lower()}(func: type("{dgraph_type}"), orderasc: name) {{ uid name unique_name }} '''

        query_string += '}'

        choices = dgraph.query(query_string=query_string)

        if len(self.relationship_constraint) == 1:
            self.choices = {c['uid']: c['name']
                            for c in choices[self.relationship_constraint[0].lower()]}
            self.choices_tuples = [
                (c['uid'], c['name']) for c in choices[self.relationship_constraint[0].lower()]]

        else:
            self.choices = {}
            self.choices_tuples = {}
            for dgraph_type in self.relationship_constraint:
                self.choices_tuples[dgraph_type] = [
                    (c['uid'], c['name']) for c in choices[dgraph_type.lower()]]
                self.choices.update({c['uid']: c['name']
                                     for c in choices[dgraph_type.lower()]})

    @property
    def wtf_field(self) -> TomSelectMutlitpleField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        return TomSelectMutlitpleField(label=self.label, description=self.form_description, choices=self.choices_tuples, render_kw=self.render_kw)


class MutualRelationship(_PrimitivePredicate):

    dgraph_predicate_type = 'uid'
    is_list_predicate = False
    comparison_operator = "uid_in"

    def __init__(self,
                 allow_new=False,
                 autoload_choices=True,
                 relationship_constraint=None,
                 overwrite=True, 
                 *args, **kwargs) -> None:

        super().__init__(overwrite=overwrite, *args, **kwargs)

        if isinstance(relationship_constraint, str):
            relationship_constraint = [relationship_constraint]
        self.relationship_constraint = relationship_constraint
        
        self.allow_new = allow_new

        # if we want the form field to show all choices automatically.
        self.autoload_choices = autoload_choices
        self.choices = {}
        self.choices_tuples = []
        self.entry_uid = None

    def __str__(self) -> str:
        return f'{self.predicate}'

    def __repr__(self) -> str:
        if self.predicate:
            return f'<Mutual Relationship Predicate "{self.predicate}">'
        else:
            return f'<Unbound Mutual Relationship Predicate>'


    def validate(self, data, node, facets=None) -> Union[UID, NewID, dict]:
        """
            Returns two values: 
            1) UID/NewID of target
            2) dict for target relationship
        """
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! provided value is not a UID: {data}')
            node_data = NewID(data, facets=facets, suffix="_".join(
                self.relationship_constraint)) if self.relationship_constraint else NewID(data, facets=facets)
            data_node = {'uid': node_data, self.predicate: node, 'name': data}
            if self.relationship_constraint:
                data_node.update({'dgraph.type': self.relationship_constraint})
            return node_data, data_node
        node_data = UID(uid, facets=facets)
        data_node = {'uid': node_data, self.predicate: node}
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type not in self.relationship_constraint:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! UID specified does not match constraint, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')
        return node_data, data_node

    def get_choices(self):
        assert self.relationship_constraint

        query_string = '{ '

        for dgraph_type in self.relationship_constraint:
            query_string += f'''{dgraph_type.lower()}(func: type("{dgraph_type}"), orderasc: name) {{ uid name unique_name }} '''

        query_string += '}'

        choices = dgraph.query(query_string=query_string)

        if len(self.relationship_constraint) == 1:
            self.choices = {c['uid']: c['name']
                            for c in choices[self.relationship_constraint[0].lower()]}
            self.choices_tuples = [
                (c['uid'], c['name']) for c in choices[self.relationship_constraint[0].lower()]]

        else:
            self.choices = {}
            self.choices_tuples = {}
            for dgraph_type in self.relationship_constraint:
                self.choices_tuples[dgraph_type] = [
                    (c['uid'], c['name']) for c in choices[dgraph_type.lower()]]
                self.choices.update({c['uid']: c['name']
                                     for c in choices[dgraph_type.lower()]})

    @property
    def wtf_field(self) -> TomSelectField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        return TomSelectField(label=self.label, description=self.form_description, choices=self.choices_tuples, render_kw=self.render_kw)


class MutualListRelationship(MutualRelationship):

    dgraph_predicate_type = '[uid]'
    is_list_predicate = True

    def validate(self, data, node, facets=None) -> Union[UID, NewID, dict]:
        if isinstance(data, (str)):
            data = data.split(',')

        node_data = []
        data_node = []
        for item in data:
            n2d, d2n = super().validate(item, node, facets)
            node_data.append(n2d)
            data_node.append(d2n)

        # permutate all relationships
        all_uids = [item for item in node_data]
        all_uids.append(node)
        for item in data_node:
            item[self.predicate] = [
                uid for uid in all_uids if uid != item['uid']]

        return node_data, data_node

    @property
    def wtf_field(self) -> TomSelectField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        return TomSelectMutlitpleField(label=self.label, description=self.form_description, choices=self.choices_tuples, render_kw=self.render_kw)


"""
    Predicate Classes
"""


class String(Predicate):

    dgraph_predicate_type = 'string'
    is_list_predicate = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class UIDPredicate(Predicate):

    dgraph_predicate_type = 'uid'
    is_list_predicate = False
    comparison_operator = 'uid_in'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(read_only=True, hidden=True, new=False,
                         default=NewID('_:newentry'), *args, **kwargs)

    def validate(self, uid, **kwargs):
        if not validate_uid(uid):
            raise InventoryValidationError(f'This is not a uid: {uid}')
        else:
            return UID(uid)


class Integer(Predicate):

    dgraph_predicate_type = 'int'
    is_list_predicate = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validation_hook(self, data):
        return int(data)

    @property
    def wtf_field(self) -> IntegerField:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return IntegerField(label=self.label, validators=validators, description=self.form_description)

    @property
    def query_field(self) -> IntegerField:
        self._prepare_query_field()
        return IntegerField(label=self.label, render_kw=self.render_kw)

class ListString(String):

    dgraph_predicate_type = '[string]'
    is_list_predicate = True

    def __init__(self, delimiter=',', overwrite=True, *args, **kwargs) -> None:
        self.delimiter = delimiter
        super().__init__(overwrite=overwrite, *args, **kwargs)

    def validation_hook(self, data):
        if not isinstance(data, (list, tuple, set, str)):
            raise InventoryValidationError(
                f'Error in <{self.predicate}> Provided data is not a list, tuple, str or set: {data}')
        if type(data) == str:
            data = data.split(self.delimiter)
        return [item.strip() for item in data if item.strip() != '']


class UniqueName(String):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(required=True, new=False,
                         permission=USER_ROLES.Reviewer, *args, **kwargs)

    @property
    def default(self):
        return None

    # def validate(self, data, uid):
    #     data = str(data)
    #     check = dgraph.get_uid(self.predicate, data)
    #     if check:
    #         if check != str(uid):
    #             raise InventoryValidationError(
    #                 'Unique Name already taken!')
    #     return slugify(data, separator="_")


class SingleChoice(String):

    def __init__(self, choices: dict = None, default='NA', radio_field=False, *args, **kwargs) -> None:

        super().__init__(*args, **kwargs)

        self.choices = choices or {'NA': 'NA'}
        self.choices_tuples = [(k, v) for k, v in self.choices.items()]
        self.values = list(self.choices.keys())
        self.radio_field = radio_field

    def validation_hook(self, data):
        if str(data) in self.values:
            return str(data)
        else:
            raise InventoryValidationError(
                f"Wrong value provided for {self.predicate}: {data}. Value has to be one of {', '.join(self.values)}")

    def set_choices(self, choices: dict) -> None:
        self.choices = choices
        self.choices_tuples = [(k, v) for k, v in self.choices.items()]
        self.values = list(self.choices.keys())

    @property
    def wtf_field(self) -> Union[SelectField, TomSelectField, RadioField]:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        if self.tom_select:
            return TomSelectField(label=self.label, validators=validators, description=self.form_description,
                                  choices=self.choices_tuples, render_kw=self.render_kw)
        elif self.radio_field:
            return RadioField(label=self.label, validators=validators, description=self.form_description,
                              choices=self.choices_tuples, render_kw=self.render_kw)
        else:
            return SelectField(label=self.label, validators=validators, description=self.form_description,
                               choices=self.choices_tuples, render_kw=self.render_kw)

    @property
    def query_field(self) -> TomSelectMutlitpleField:
        self._prepare_query_field()
        return TomSelectMutlitpleField(label=self.label, choices=self.choices_tuples, render_kw=self.render_kw)


class MultipleChoice(SingleChoice):

    dgraph_predicate_type = '[string]'
    is_list_predicate = True

    def __init__(self, overwrite=True, *args, **kwargs) -> None:
        super().__init__(overwrite=overwrite, *args, **kwargs)

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

        return data

    @property
    def wtf_field(self) -> Union[SelectMultipleField, TomSelectMutlitpleField]:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        if self.tom_select:
            return TomSelectMutlitpleField(label=self.label, validators=validators, description=self.form_description,
                                           choices=self.choices_tuples, render_kw=self.render_kw)
        return SelectMultipleField(label=self.label, validators=validators, description=self.form_description,
                                   choices=self.choices_tuples, render_kw=self.render_kw)

    @property
    def query_field(self) -> TomSelectMutlitpleField:
        self._prepare_query_field()
        return TomSelectMutlitpleField(label=self.label, choices=self.choices_tuples, render_kw=self.render_kw)


class DateTime(Predicate):

    dgraph_predicate_type = 'datetime'
    is_list_predicate = False
    comparison_operator = 'between'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validation_hook(self, data):
        if isinstance(data, (datetime.date, datetime.datetime)):
            return data
        elif isinstance(data, int):
            try:
                return datetime.date(year=data, month=1, day=1)
            except:
                pass
        try:
            return dateparser.parse(data)
        except:
            raise InventoryValidationError(
                f'Error in <{self.predicate}> Cannot parse provided value to date: {data}')

    @property
    def wtf_field(self) -> Union[DateField, NullableDateField]:
        render_kw = {'type': 'date'}
        if self.render_kw:
            render_kw = {**self.render_kw, **render_kw}
        if self.required:
            return DateField(label=self.label, description=self.form_description, render_kw=render_kw)
        else:
            return NullableDateField(label=self.label, description=self.form_description, render_kw=render_kw)

    @property
    def query_field(self) -> IntegerField:
        self._prepare_query_field()
        render_kw = {'step': 1, 'min': 1500, 'max': 2100}
        if self.render_kw:
            render_kw = {**self.render_kw, **render_kw}
        return IntegerField(label=self.label, render_kw=self.render_kw)

    def query_filter(self, vals: Union[str, list, int], custom_operator: Union['lt', 'gt']=None):
        if vals is None:
            return f'has({self.predicate})'
            
        if isinstance(vals, list) and len(vals) > 1:
            vals = [self.validation_hook(val) for val in vals[:2]]
            return f'{self.comparison_operator}({self.predicate}, "{vals[0].year}-01-01", "{vals[1].year}-12-31")'

        else:
            if isinstance(vals, list):
                vals = vals[0]
            date = self.validation_hook(vals)
            if custom_operator:
                return f'{custom_operator}({self.predicate}, "{date.year}")'
            else:
                return f'{self.comparison_operator}({self.predicate}, "{date.year}-01-01", "{date.year}-12-31")'

class Year(DateTime):

    def validation_hook(self, data):
        if type(data) in [datetime.date, datetime.datetime]:
            return data
        else:
            try:
                return datetime.datetime(year=int(data), month=1, day=1)
            except:
                raise InventoryValidationError(
                    f'Cannot parse provided value to year: {data}')

    @property
    def wtf_field(self) -> IntegerField:
        render_kw = {'step': 1, 'min': 1500, 'max': 2100}
        if self.render_kw:
            render_kw = {**self.render_kw, **render_kw}
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional(strip_whitespace=True)]
        return IntegerField(label=self.label, description=self.form_description, render_kw=render_kw, validators=validators)


class Boolean(Predicate):

    """
        Boolean Predicate (True / False). 
        Default always `False`. To change this behaviour set the `default` parameter to `True`

        :param label:
            User facing label for predicate, 
            default: automatically generated from 'predicate'
        :param default (False):
            Default value when validating when nothing is specified
        :param description:
            Passes description to WTF Field, will be rendered next to check box.
            E.g., "Yes, I agree"
    """

    dgraph_predicate_type = 'bool'
    is_list_predicate = False

    def __init__(self, label: str = None, default=False, overwrite=True, **kwargs) -> None:
        super().__init__(label, default=default, overwrite=overwrite, **kwargs)

    def validation_hook(self, data):
        if isinstance(data, bool):
            return bool(data)
        elif isinstance(data, str):
            return data.lower() in ('yes', 'true', 't', '1', 'y')
        elif isinstance(data, int):
            return data > 0
        else:
            raise InventoryValidationError(
                f'Cannot evaluate provided value as bool: {data}!')

    def query_filter(self, vals, custom_operator=None):
        if isinstance(vals, list):
            vals = vals[0]

        # use DGraph native syntax first
        if vals in ['true', 'false']:
            return super().query_filter(vals)

        else:
            # try to coerce to bool
            vals = self.validation_hook(vals)
            try:
                return super().query_filter(str(vals).lower())
            except: 
                return f'has({self.predicate})'
            

    @property
    def wtf_field(self) -> BooleanField:
        return BooleanField(label=self.label, description=self.form_description)

    @property
    def query_field(self) -> BooleanField:
        self._prepare_query_field()
        self.render_kw.update({'value': 'true'})
        return BooleanField(label=self.label, render_kw=self.render_kw)


class Geo(Predicate):

    dgraph_predicate_type = 'geo'
    is_list_predicate = False
    geo_type = 'Point'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def str2geo(self, data: str) -> Union[GeoScalar, None]:
        try:
            geo = geocode(data.strip())
            return GeoScalar(self.geo_type, coordinates=[
                float(geo.get('lon')), float(geo.get('lat'))])
        except:
            return None

    def geo2str(self, data: dict) -> Union[str, None]:
        try:
            address_lookup = reverse_geocode(
                data.get('lat'), data.get('lon'))
            return address_lookup['display_name']
        except:
            return None


class SingleRelationship(Predicate):

    dgraph_predicate_type = 'uid'
    is_list_predicate = False
    comparison_operator = 'uid_in'

    def __init__(self,
                 relationship_constraint=None,
                 allow_new=True,
                 autoload_choices=False,
                 *args, **kwargs) -> None:

        if isinstance(relationship_constraint, str):
            relationship_constraint = [relationship_constraint]
        self.relationship_constraint = relationship_constraint
        self.allow_new = allow_new

        # if we want the form field to show all choices automatically.
        self.autoload_choices = autoload_choices
        self.choices = {}
        self.choices_tuples = []

        super().__init__(*args, **kwargs)

    def validate(self, data, facets=None) -> Union[UID, NewID, dict]:
        if data == '':
            return None
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! provided value is not a UID: {data}')
            d = {'uid': NewID(data, facets=facets, suffix="_".join(
                self.relationship_constraint)) if self.relationship_constraint else NewID(data, facets=facets)}
            if self.relationship_constraint:
                d.update({'dgraph.type': self.relationship_constraint})
            return d
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type not in self.relationship_constraint:
                raise InventoryValidationError(
                    f'Error in <{self.predicate}>! UID specified does not match constrain, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')
        return {'uid': UID(uid, facets=facets)}

    def get_choices(self):
        assert self.relationship_constraint

        query_string = '{ '

        for dgraph_type in self.relationship_constraint:
            query_string += f'''{dgraph_type.lower()}(func: type("{dgraph_type}"), orderasc: name) {{ uid name unique_name }} '''

        query_string += '}'

        choices = dgraph.query(query_string=query_string)

        if len(self.relationship_constraint) == 1:
            self.choices = {c['uid']: c.get('name') or c.get('unique_name')
                            for c in choices[self.relationship_constraint[0].lower()]}
            self.choices_tuples = [
                (c['uid'], c.get('name') or c.get('unique_name')) for c in choices[self.relationship_constraint[0].lower()]]
            self.choices_tuples.insert(0, ('', ''))

        else:
            self.choices = {}
            self.choices_tuples = {}
            for dgraph_type in self.relationship_constraint:
                self.choices_tuples[dgraph_type] = [
                    (c['uid'], c.get('name') or c.get('unique_name')) for c in choices[dgraph_type.lower()]]
                self.choices.update({c['uid']: c.get('name') or c.get('unique_name')
                                     for c in choices[dgraph_type.lower()]})

    @property
    def wtf_field(self) -> TomSelectField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return TomSelectField(label=self.label, 
                                validators=validators, 
                                description=self.form_description, 
                                choices=self.choices_tuples, 
                                render_kw=self.render_kw)

    @property
    def query_field(self) -> TomSelectMutlitpleField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        self._prepare_query_field()
        return TomSelectMutlitpleField(label=self.label, 
                                        choices=self.choices_tuples, 
                                        render_kw=self.render_kw)


class ListRelationship(SingleRelationship):

    dgraph_predicate_type = '[uid]'
    is_list_predicate = True

    def __init__(self, overwrite=True, relationship_constraint=None, allow_new=True, autoload_choices=False, *args, **kwargs) -> None:
        super().__init__(relationship_constraint=relationship_constraint, allow_new=allow_new,
                         autoload_choices=autoload_choices, overwrite=overwrite, *args, **kwargs)

    def validate(self, data, facets=None) -> list:
        if isinstance(data, str):
            data = data.split(',')
        data = set([item.strip() for item in data if item.strip() != ''])
        uids = []
        for item in data:
            uid = super().validate(item, facets=facets)
            if uid:
                uids.append(uid)

        return uids

    @property
    def wtf_field(self) -> TomSelectMutlitpleField:
        if self.autoload_choices and self.relationship_constraint:
            self.get_choices()
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return TomSelectMutlitpleField(label=self.label,
                                       validators=validators,
                                       description=self.form_description,
                                       choices=self.choices_tuples,
                                       render_kw=self.render_kw)


""" Functions for making nquad statements """


def _enquote(string) -> str:
    return f'"{string}"'


def make_nquad(s, p, o) -> str:
    """ Strings, Ints, Floats, Bools, Date(times) are converted automatically to Scalar """

    if not isinstance(s, (UID, NewID, Variable)):
        s = NewID(s)

    if not isinstance(p, Predicate):
        p = Predicate.from_key(p)

    if not isinstance(o, (list, set, Scalar, Variable, UID, NewID)):
        o = Scalar(o)

    nquad_string = f'{s.nquad} {p.nquad} {o.nquad}'

    if hasattr(o, "facets"):
        if o.facets is not None:
            facets = []
            for key, val in o.facets.items():
                if type(val) in [datetime.date, datetime.datetime]:
                    facets.append(f'{key}={val.isoformat()}')
                elif type(val) in [int, float]:
                    facets.append(f'{key}={val}')
                else:
                    facets.append(f'{key}={_enquote(val)}')
            nquad_string += f' ({", ".join(facets)})'

    nquad_string += ' .'
    return nquad_string


def dict_to_nquad(d: dict) -> list:
    if d.get('uid'):
        uid = d['uid']
    else:
        uid = NewID('_:newentry')
    nquads = []
    for key, val in d.items():
        if val is None:
            continue
        if key == 'uid':
            continue
        if not isinstance(key, Predicate):
            key = Predicate.from_key(key)
        if isinstance(val, (list, set)):
            if len(val) > 0:
                for item in val:
                    nquads.append(make_nquad(uid, key, item))
        else:
            nquads.append(make_nquad(uid, key, val))

    return nquads
