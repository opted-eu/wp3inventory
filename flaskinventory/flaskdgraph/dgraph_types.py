""" 
    Classes to represent DGraph objects in Python
    These are helper classes to automatically generate
    nquad statements from dictionaries
    May later be used for automatic query building
"""

from typing import Union
import datetime
import json

# external utils
from slugify import slugify
import secrets
from dateutil import parser as dateparser


from flaskinventory import dgraph

from .customformfields import NullableDateField, TomSelectField, TomSelectMutlitpleField
from .utils import validate_uid

from flaskinventory.errors import InventoryPermissionError, InventoryValidationError
from flaskinventory.add.external import geocode, reverse_geocode
from flaskinventory.users.constants import USER_ROLES

from wtforms import StringField, SelectField, DateField, BooleanField, SubmitField, RadioField
from wtforms.fields.core import SelectMultipleField
from wtforms.fields.simple import TextAreaField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import DataRequired, Optional


"""
    DGraph Primitives
"""


class UID:

    def __init__(self, uid, facets=None):
        self.uid = uid.strip()
        if facets:
            self.facets = facets

    def __str__(self) -> str:
        return f'{self.uid}'

    def __repr__(self) -> str:
        return f'<{self.uid}>'

    @property
    def nquad(self) -> str:
        return f'<{self.uid}>'

    @property
    def query(self) -> str:
        return f'{self.uid}'


class NewID:

    def __init__(self, newid, facets=None):
        if newid.startswith('_:'):
            self.newid = newid.strip()
        else:
            self.newid = f'_:{slugify(newid, separator="_")}'

        if facets:
            self.facets = facets

    def __str__(self) -> str:
        return self.newid

    def __repr__(self) -> str:
        return f'{self.newid}'

    @property
    def nquad(self) -> str:
        return f'{self.newid}'


class Predicate:

    """
        Base Class for representing DGraph Predicates
        Is used for validating data, generating DGraph queries & mutations,
        and also provides generators for WTF Form Fields

    """

    # corresponds to the type of the predicate
    dgraph_predicate_type = 'string'

    def __init__(self,
                 label: str = None,
                 default: str = None,
                 required=False,
                 overwrite=False,
                 new=True,
                 edit=True,
                 permission=USER_ROLES.Contributor,
                 read_only=False,
                 hidden=False,
                 description='',
                 tom_select=False,
                 render_kw: dict = None,
                 large_textfield=False) -> None:
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

        self.predicate = None
        self._label = label
        self.read_only = read_only
        self.hidden = hidden
        self.new = new
        self.edit = edit
        self.permission = permission

        # WTF Forms
        self.required = required
        self.form_description = description
        self.tom_select = tom_select
        self.render_kw = render_kw
        self.large_textfield = large_textfield

        if hidden and self.render_kw:
            self.render_kw.update(hidden=hidden)
        else:
            self.render_kw = {'hidden': hidden}
        
        if read_only and self.render_kw:
            self.render_kw.update(readonly=read_only)
        else:
            self.render_kw = {'readonly': read_only}
        

        # default value applied when nothing is specified
        self._default = default

        # delete all values first before writing new ones
        self.overwrite = overwrite

        # for k, v in kwargs.items():
        #     if hasattr(self, k):
        #         setattr(self, k, v)

    def __str__(self) -> str:
        return f'{self.predicate}'

    def __repr__(self) -> str:
        if self.predicate:
            return f'<DGraph Predicate "{self.predicate}">'
        else:
            return f'<Unbound DGraph Predicate>'

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
            value = value.isoformat()
        elif type(value) is bool:
            value = str(value).lower()

        self.value = str(value).strip()
        if self.value != '*':
            self.value = json.dumps(self.value)
        if facets:
            self.facets = facets

    def __str__(self) -> str:
        return f'{self.value}'

    def __repr__(self) -> str:
        return f'{self.value}'

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

    def __init__(self, geotype, coordinates):
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

    def __str__(self) -> str:
        return str(self.value)

    @property
    def nquad(self) -> str:
        return '"' + str(self.value) + '"^^<geo:geojson>'


class Variable:

    def __init__(self, var, predicate, val=False):
        self.var = var
        self.predicate = predicate
        self.val = val

    def __str__(self) -> str:
        return f'{self.var}'

    def __repr__(self) -> str:
        return f'{self.var} as {self.predicate}'

    def nquad(self) -> str:
        if self.val:
            return f'val({self.var})'
        else:
            return f'uid({self.var})'

    def query(self) -> str:
        return f'{self.var} as {self.predicate}'


"""
    Predicate Classes
"""


class String(Predicate):

    dgraph_predicate_type = 'string'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validate(self, data, strip=True):
        if strip:
            return str(data).strip()
        else:
            return str(data)

class UIDPredicate(Predicate):

    dgraph_predicate_type = 'uid'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(read_only=True, hidden=True, new=False, default=NewID('_:newentry'), *args, **kwargs)

    def validate(self, uid):
        if not validate_uid(uid):
            raise InventoryValidationError(f'This is not a uid: {uid}')
        else:
            return UID(uid)

class Integer(Predicate):

    dgraph_predicate_type = 'int'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validate(self, data):
        return int(data)

    @property
    def wtf_field(self) -> IntegerField:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return IntegerField(label=self.label, validators=validators, description=self.form_description)


class ListString(String):

    dgraph_predicate_type = '[string]'

    def validate(self, data, strip=True):
        print(data, type(data))
        if type(data) == str:
            data = data.split(',')

        if strip:
            return set([item.strip() for item in data if item.strip() != ''])
        else:
            return set([item for item in data if item.strip() != ''])


class UniqueName(String):

    @property
    def default(self):
        return slugify(secrets.token_urlsafe(8), separator="_")

    # def validate(self, data, uid):
    #     data = str(data)
    #     check = dgraph.get_uid(self.dgraph_name, data)
    #     if check:
    #         if check != str(uid):
    #             raise InventoryValidationError(
    #                 'Unique Name already taken!')
    #     return slugify(data, separator="_")


class SingleChoice(String):

    def __init__(self, choices: dict = None, default='NA', *args, **kwargs) -> None:

        super().__init__(*args, **kwargs)

        self.choices = choices or {'NA': 'NA'}
        self.choices_tuple = [(k, v) for k, v in self.choices.items()]
        self.values = list(self.choices.keys())

    def validate(self, data):
        if str(data) in self.values:
            return data
        else:
            raise InventoryValidationError(
                f"Wrong value provided for {self.dgraph_name}: {data}. Value has to be one of {', '.join(self.values)}")

    def set_choices(self, choices: dict) -> None:
        self.choices = choices
        self.choices_tuple = [(k, v) for k, v in self.choices.items()]
        self.values = list(self.choices.keys())

    @property
    def wtf_field(self) -> Union[SelectField, TomSelectField]:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        if self.tom_select:
            return TomSelectField(label=self.label, validators=validators, description=self.form_description,
                                  choices=self.choices_tuple)
        return SelectField(label=self.label, validators=validators, description=self.form_description,
                           choices=self.choices_tuple)


class DateTime(Predicate):

    dgraph_predicate_type = 'datetime'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validate(self, data):
        if type(data) in [datetime.date, datetime.datetime]:
            return data
        else:
            try:
                return dateparser.parse(str(data))
            except:
                raise InventoryValidationError(
                    f'Cannot parse provided value to date: {data}')

    @property
    def wtf_field(self) -> Union[DateField, NullableDateField]:
        render_kw = {'type': 'date'}
        if self.render_kw:
            render_kw = {**self.render_kw, **render_kw}
        if self.required:
            return DateField(label=self.label, description=self.form_description, render_kw=render_kw)
        else:
            return NullableDateField(label=self.label, description=self.form_description, render_kw=render_kw)


class Boolean(Predicate):

    dgraph_predicate_type = 'bool'

    def validate(self, data):
        if isinstance(data, bool):
            return bool(data)
        elif isinstance(data, str):
            return data.lower() in ('yes', 'true', 't', '1')
        elif isinstance(data, int):
            return data > 0
        else:
            raise InventoryValidationError(
                f'Cannot evaluate provided value as bool: {data}!')

    @property
    def wtf_field(self) -> BooleanField:
        return BooleanField(label=self.label, description=self.form_description)


class Geo(Predicate):

    dgraph_predicate_type = 'geo'
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


class GeoAutoCode(Geo):

    autoinput = 'address_string'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def autocode(self, data) -> Union[GeoScalar, None]:
        return self.str2geo(data)


class AddressAutocode(Geo):

    autoinput = 'name'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validate(self, data, strip=True):
        if strip:
            return str(data).strip()
        else:
            return str(data)

    def autocode(self, data: str) -> Union[dict, None]:
        query_result = self.str2geo(data)
        geo_result = None
        if query_result:
            geo_result = {'address_geo': query_result}
            address_lookup = reverse_geocode(
                query_result.lat, query_result.lon)
            geo_result['address_string'] = address_lookup.get('display_name')
        return geo_result


class SingleRelationship(Predicate):

    dgraph_predicate_type = 'uid'

    def __init__(self, relationship_constraint: str = None, allow_new=True, choices=[], *args, **kwargs) -> None:
        self.relationship_constraint = relationship_constraint
        self.allow_new = allow_new
        self.choices = choices

        super().__init__(*args, **kwargs)

    def validate(self, data) -> Union[UID, NewID]:
        uid = validate_uid(data)
        if not uid:
            if not self.allow_new:
                raise InventoryValidationError(
                    f'Error in {self.dgraph_name}! provided value is not a UID: {data}')
            return NewID(data)
        if self.relationship_constraint:
            entry_type = dgraph.get_dgraphtype(uid)
            if entry_type != self.relationship_constraint:
                raise InventoryValidationError(
                    f'UID specified does not match constrain, UID is not a {self.relationship_constraint}!: uid <{uid}> <dgraph.type> <{entry_type}>')
        return UID(uid)

    @property
    def wtf_field(self) -> TomSelectField:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return TomSelectField(label=self.label, validators=validators, description=self.form_description, choices=self.choices, render_kw=self.render_kw)


class ListRelationship(SingleRelationship):

    dgraph_predicate_type = '[uid]'

    def validate(self, data) -> list:
        if type(data) == str:
            data = data.split(',')
        uids = []
        for item in data:
            uid = validate_uid(item)
            if not uid:
                if not self.allow_new:
                    raise InventoryValidationError(
                        f'Error in <{self.dgraph_name}>! provided value is not a UID: {data}')
                uids.append(NewID(item))
            else:
                if self.relationship_constraint:
                    entry_type = dgraph.get_dgraphtype(uid)
                    if entry_type != self.relationship_constraint:
                        raise InventoryValidationError(
                            f'UID specified does not match constrain, UID is not a {self.relationship_constraint}! uid <{uid}> <dgraph.type> <{entry_type}>')
                uids.append(UID(uid))
        return set(uids)

    @property
    def wtf_field(self) -> TomSelectMutlitpleField:
        if self.required:
            validators = [DataRequired()]
        else:
            validators = [Optional()]
        return TomSelectMutlitpleField(label=self.label, validators=validators, description=self.form_description, choices=self.choices, render_kw=self.render_kw)


""" Functions for making nquad statements """


def _enquote(string) -> str:
    return f'"{string}"'


def make_nquad(s, p, o) -> str:
    """ Strings, Ints, Floats, Bools, Date(times) are converted automatically to Scalar """

    if not isinstance(s, (UID, NewID)):
        p = NewID(p)

    if not isinstance(p, Predicate):
        p = Predicate.from_key(p)

    if not isinstance(o, (list, set, Scalar, Variable, UID, NewID)):
        o = Scalar(o)

    nquad_string = f'{s.nquad} {p.nquad} {o.nquad}'

    if hasattr(o, 'facets'):
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


def dict_to_nquad(d) -> list:
    if d.get('uid'):
        uid = d.pop('uid')
    else:
        uid = NewID('_:newentry')
    nquads = []
    for key, val in d.items():
        if not isinstance(key, Predicate):
            key = Predicate.from_key(key)
        if isinstance(val, (list, set)):
            if len(val) > 0:
                for item in val:
                    nquads.append(make_nquad(uid, key, item))
        else:
            nquads.append(make_nquad(uid, key, val))

    return nquads
