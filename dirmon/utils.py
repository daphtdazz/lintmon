def colour_text(text, foreground='white', background='black'):
    foreground_colours = {
        'black': '30',
        'red': '31',
        'green': '32',
        'yellow': '33',
        'blue': '34',
        'pink': '35',
        'cyan': '36',
        'grey': '37',
        'gray': '37',
        'white': '38',
    }
    background_colours = {
        'black': '40',
        'red': '41',
        'green': '42',
        'yellow': '43',
        'blue': '44',
        'pink': '45',
        'cyan': '46',
        'grey': '47',
        'gray': '47',
    }

    fg = foreground_colours[foreground]
    bg = background_colours[background]

    return f'\x1b[{fg}m\x1b[{bg}m{text}\x1b[0m'


def diff_problem_lines(lines_before, lines_after):
    lines_before_set = {(file, line) for file, lines in lines_before.items() for line in lines}
    lines_after_set = {(file, line) for file, lines in lines_after.items() for line in lines}
    before_not_after = lines_before_set - lines_after_set
    after_not_before = lines_after_set - lines_before_set
    return [
        (plus_minus, file, line)
        for plus_minus, set_ in [('-', before_not_after), ('+', after_not_before)]
        for file, line in set_
    ]


def first(iter_):
    for item in iter_:
        return item

    return None


def gb(iter_, func):
    dct = {}
    for thing in iter_:
        key = func(thing)
        if key is None:
            continue
        dct.setdefault(key, []).append(thing)
    return dct


def lf(func, iter_):
    return list(filter(func, iter_))
