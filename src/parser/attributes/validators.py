from typing import Collection, List
from urllib.parse import urlparse

from src.parser.error import ValidationError


def validate_absolute_url(value: str) -> list[ValidationError]:
    try:
        result = urlparse(value)
        is_valid = all([result.scheme, result.netloc])
        if not is_valid:
            return [ValidationError.bad_url(value)]
        return []
    except ValueError:
        return [ValidationError.bad_url(value)]


def validate_single_primary_value(value: Collection[dict]) -> list[ValidationError]:
    errors = []
    primary_entries = set()
    for i, item in enumerate(value):
        if item.get("primary") is True:
            primary_entries.add(i)
    if len(primary_entries) > 1:
        errors.append(ValidationError.multiple_primary_values(primary_entries))
    # TODO: warn if a given type-value pair appears more than once
    return errors
