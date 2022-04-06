def IMD2dict(IMD):
    """ utility function for converting ImmutableMultiDict to an ordinary dict 
        useful for `request.form` which comes in this format
    """
    d = IMD.to_dict(flat=False)
    for k, v in d.items():
        if isinstance(v, list) and len(v) == 1:
            d[k] = v[0]
    return d