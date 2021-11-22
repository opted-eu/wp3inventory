import re

def strip_query(query):
    # Dgraph query strings have some weaknesses 
    # towards certain special characters
    # for term matching and regex these characters
    # can simply be removed
    return re.sub(r'"|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*|\.', '', query)

def escape_query(query):
    return re.sub(r'("|/|\\|\(|\)|<|>|\{|\}|\[|\]|\$|&|#|\+|\^|\?|\*|\.)', r'\\\1', query)