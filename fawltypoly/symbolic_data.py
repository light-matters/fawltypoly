"""Read the arithmetic EDN subset, including scientific numbers and ratios.

Basilisp 0.5.1's EDN reader does not parse those number formats. Its full reader
does, so exclude reader macros first and use it only to construct data.
"""

from basilisp.lang import reader


def loads(text):
    in_string = escaped = in_comment = False
    for char in text:
        if in_comment:
            if char in "\r\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == ";":
            in_comment = True
        elif char in "#'`~@^\\":
            raise ValueError("Reader macros, tagged literals, metadata and character forms are not supported")
    forms = list(reader.read_str(text))
    if len(forms) != 1:
        raise ValueError("Expected exactly one symbolic data form")
    return forms[0]
