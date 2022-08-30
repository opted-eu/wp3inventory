import re


def IMD2dict(IMD):
    """ utility function for converting ImmutableMultiDict to an ordinary dict 
        useful for `request.form` which comes in this format
    """
    d = IMD.to_dict(flat=False)
    for k, v in d.items():
        if isinstance(v, list) and len(v) == 1:
            d[k] = v[0]
    return d


DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$", flags=re.IGNORECASE)


def validate_doi(doi):
    if DOI_REGEX.fullmatch(doi.strip()):
        return True
    else:
        return False
