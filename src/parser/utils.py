def lower_dict_keys(d: dict) -> dict:
    d_lowered = {}
    for k, v in d.items():
        if isinstance(v, list):
            d_lowered[k.lower()] = [lower_dict_keys(i) if isinstance(i, dict) else i for i in v]
        elif isinstance(v, dict):
            d_lowered[k.lower()] = lower_dict_keys(v)
        else:
            d_lowered[k.lower()] = v
    return d_lowered
