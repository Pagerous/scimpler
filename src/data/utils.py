import re
from typing import Any, Optional
from uuid import uuid4

OP_REGEX = re.compile(r"\s+", flags=re.DOTALL)
PLACEHOLDER_REGEX = re.compile(r"\|&PLACE_HOLDER_(\w+)&\|")
STRING_VALUES_REGEX = re.compile(r"'(.*?)'|\"(.*?)\"", flags=re.DOTALL)


def get_placeholder() -> tuple[str, str]:
    id_ = uuid4().hex
    return id_, f"|&PLACE_HOLDER_{id_}&|"


def deserialize_placeholder(exp: str) -> Optional[str]:
    match = PLACEHOLDER_REGEX.fullmatch(exp)
    if match:
        return match.group(1)
    return None


def encode_strings(exp: str) -> tuple[str, dict[str, Any]]:
    placeholders = {}
    for match in STRING_VALUES_REGEX.finditer(exp):
        start, stop = match.span()
        string_value = match.string[start:stop]
        id_, placeholder = get_placeholder()
        placeholders[id_] = string_value
        exp = exp.replace(string_value, placeholder, 1)
    return exp, placeholders


def decode_placeholders(exp: str, placeholders: dict[str, Any]) -> str:
    encoded = exp
    for match in PLACEHOLDER_REGEX.finditer(exp):
        id_ = match.group(1)
        if id_ in placeholders:
            encoded = encoded.replace(match.group(0), str(placeholders[id_]))
    return encoded


def deserialize_comparison_value(value: str) -> Any:
    if (
        value.startswith('"')
        and value.endswith('"')
        or value.startswith("'")
        and value.endswith("'")
    ):
        value = value[1:-1]
    elif value == "false":
        value = False
    elif value == "true":
        value = True
    elif value == "null":
        value = None
    else:
        deserialized = float(value)
        deserialized_int = int(deserialized)
        if deserialized == deserialized_int:
            value = deserialized_int
        else:
            value = deserialized
    return value
