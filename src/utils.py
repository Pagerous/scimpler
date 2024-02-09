import re
from typing import Any, Optional

OP_REGEX = re.compile(r"\s+", flags=re.DOTALL)
PLACEHOLDER_REGEX = re.compile(r"\|&PLACE_HOLDER_(\d+)&\|")
STRING_VALUES_REGEX = re.compile(r"'(.*?)'|\"(.*?)\"", flags=re.DOTALL)


def get_placeholder(index: int) -> str:
    return f"|&PLACE_HOLDER_{index}&|"


def parse_placeholder(exp: str) -> Optional[int]:
    match = PLACEHOLDER_REGEX.fullmatch(exp)
    if match:
        return int(match.group(1))
    return None


def parse_comparison_value(value: str) -> Any:
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
        parsed = float(value)
        parsed_int = int(parsed)
        if parsed == parsed_int:
            value = parsed_int
        else:
            value = parsed
    return value
