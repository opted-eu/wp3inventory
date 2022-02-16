import re

def strip_query(query):
    # Dgraph query strings have some weaknesses 
    # towards certain special characters
    # for term matching and regex these characters
    # can simply be removed
    return re.sub(r'"|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*', '', query)

def escape_query(query):
    return re.sub(r'("|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*)', r'\\\1', query)

def validate_uid(uid):
    if type(uid) == str:
        uid = uid.lower()
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

def author_sequence(paper, author_key='authors', sequence_key='sequence'):
    author_sequence = {int(k): v for k, v in sorted(paper[author_key + '|' + sequence_key].items(), key=lambda item: item[1])}
    return [paper[author_key][k] for k, _ in author_sequence.items()]