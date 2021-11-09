""" 
    Classes to represent DGraph types in Python
    These are helper classes to automatically generate
    nquad statements from dictionaries
    May later be used for automatic query building
"""


import datetime
import json
from slugify import slugify


class UID:

    def __init__(self, uid, facets=None):
        self.uid = uid.strip()
        if facets:
            self.facets = facets

    def __str__(self) -> str:
        return f'{self.uid}'

    def __repr__(self) -> str:
        return f'<{self.uid}>'

    def nquad(self) -> str:
        return f'<{self.uid}>'

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

    def nquad(self) -> str:
        return f'{self.newid}'


class Predicate:

    def __init__(self, predicate):
        self.predicate = predicate.strip()

    def __str__(self) -> str:
        return f'{self.predicate}'

    def __repr__(self) -> str:
        return f'{self.predicate}'

    def nquad(self) -> str:
        if self.predicate == '*':
            return '*'
        else:
            return f'<{self.predicate}>'

    def query(self) -> str:
        return f'{self.predicate}'


class Scalar:

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

    def nquad(self) -> str:
        if self.value == '*':
            return '*'
        else:
            return f'''{self.value}'''


class Geolocation:

    def __init__(self, geotype, coordinates):
        self.geotype = geotype
        for coord in coordinates:
            round(coord, 12)
        self.coordinates = coordinates
        self.geojson = {'type': geotype, 'coordinates': coordinates}

    def __str__(self) -> str:
        return str(self.geojson)

    def nquad(self) -> str:
        return '"' + str(self.geojson) + '"^^<geo:geojson>'


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


""" Functions for making nquad statements """


def _enquote(string) -> str:
    return f'"{string}"'


def make_nquad(s, p, o) -> str:
    """ Strings, Ints, Floats, Bools, Date(times) are converted automatically to Scalar """

    if type(o) not in [list, Scalar, Variable, UID, NewID, Geolocation]:
        o = Scalar(o)

    nquad_string = f'{s.nquad()} {p.nquad()} {o.nquad()}'

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
        if type(val) == list:
            if len(val) > 0:
                for item in val:
                    nquads.append(make_nquad(uid, Predicate(key), item))
        else:
            nquads.append(make_nquad(uid, Predicate(key), val))

    return nquads
