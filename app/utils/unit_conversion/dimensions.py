import re

DIMENSIONS = {
    'L': '[length]', 'M': '[mass]', 'T': '[time]', 'I': '[current]',
    'K': '[temperature]', 'D': '[temperature]', 'J': '[luminosity]',
    'N': '[substance]', 'A': None, 'S': None,
}

def dimension_terms(text: str) -> dict[str, int]:
    if text == 'none':
        raise ValueError('Dictionary declares a special, non-dimensional unit.')
    if not re.fullmatch(r'(?:1|(?:[A-Z][0-9]*)+)(?:/(?:[A-Z][0-9]*)+)?', text):
        raise ValueError(f'Unsupported dimension notation: {text}')
    result: dict[str, int] = {}
    for i, part in enumerate(text.split('/')):
        for letter, exponent in re.findall(r'([A-Z])([0-9]*)', part):
            if letter not in DIMENSIONS:
                raise ValueError(f'Unknown dimension: {letter}')
            result[letter] = result.get(letter, 0) + (1 if i == 0 else -1) * int(exponent or 1)
    return {k: v for k, v in result.items() if v}

def physical_dimensions(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for letter, exponent in dimension_terms(text).items():
        name = DIMENSIONS[letter]
        if name:
            result[name] = result.get(name, 0) + exponent
    return {k: v for k, v in result.items() if v}
