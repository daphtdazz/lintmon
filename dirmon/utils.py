def lf(func, iter_):
    return list(filter(func, iter_))


def gb(iter_, func):
    dct = {}
    for thing in iter_:
        key = func(thing)
        if key is None:
            continue
        dct.setdefault(key, []).append(thing)
    return dct
