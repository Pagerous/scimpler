from typing import Collection, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from src.error import ValidationError, ValidationIssues


def validate_absolute_url(value: str) -> Tuple[Optional[str], ValidationIssues]:
    issues = ValidationIssues()
    try:
        result = urlparse(value)
        is_valid = all([result.scheme, result.netloc])
        if not is_valid:
            issues.add(
                issue=ValidationError.bad_url(value),
                proceed=False,
            )
            return None, issues
    except ValueError:
        issues.add(
            issue=ValidationError.bad_url(value),
            proceed=False,
        )
        return None, issues
    return value, issues


def validate_single_primary_value(
    value: Collection[Dict],
) -> Tuple[Optional[List[Dict]], ValidationIssues]:
    issues = ValidationIssues()
    primary_entries = set()
    for i, item in enumerate(value):
        if item.get("primary") is True:
            primary_entries.add(i)
    if len(primary_entries) > 1:
        issues.add(
            issue=ValidationError.multiple_primary_values(primary_entries),
            proceed=True,
        )
    # TODO: warn if a given type-value pair appears more than once
    return list(value), issues
