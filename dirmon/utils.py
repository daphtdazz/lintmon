def lf(func, iter_):
    return list(filter(func, iter_))


def gb(iter_, func):
    dct = {}
    for thing in iter_:
        dct.setdefault(func(thing), []).append(thing)
    return dct
