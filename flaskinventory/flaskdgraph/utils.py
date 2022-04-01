import re
from typing import Any, Union

def strip_query(query):
    # Dgraph query strings have some weaknesses 
    # towards certain special characters
    # for term matching and regex these characters
    # can simply be removed
    return re.sub(r'"|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*', '', query)

def escape_query(query):
    return re.sub(r'("|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*)', r'\\\1', query)

def validate_uid(uid: Any) -> Union[str, bool]:
    """
        Utility function for validating if object is a UID
        Tries to coerce object to a str (uid)
        If fails, will return False
    """
    if not isinstance(uid, (str, int)):
        uid = str(uid)

    if type(uid) == str:
        uid = uid.lower().strip()
        if not uid.startswith('0x'):
            uid = '0x' + uid
        try:
            int(uid, 16)
        except ValueError:
            return False
        return uid
    elif type(uid) == int:
        return str(hex(uid))
    else:
        return False

def restore_sequence(d: dict, sequence_key='sequence'):
    for predicate, val in d.items():
        if isinstance(val, dict):
            restore_sequence(val, sequence_key=sequence_key)
        if isinstance(val, list):
            for subval in val:
                if isinstance(subval, dict):
                    restore_sequence(subval, sequence_key=sequence_key)
        if predicate + "|" + sequence_key in d.keys():
            ordered_sequence = {int(k): v for k, v in sorted(d[predicate + "|" + sequence_key].items(), key=lambda item: item[1])}
            d[predicate] = [d[predicate][k] for k, _ in ordered_sequence.items()]