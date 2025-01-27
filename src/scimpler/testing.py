import warnings
from collections import defaultdict
from typing import Iterable, Union

import pytest

from scimpler.error import ValidationError
from scimpler.validator import Validator
from scimpler.warning import ScimplerCompatibilityWarning


def assert_response(validator: Validator, status_code: int, **kwargs) -> None:
    """
    Asserts the response for the given validator.
    All **kwargs are passed to `Validator.validate_response` method.

    If the response validation cause warnings, `ScimplerCompatibilityWarning`
    is raised with detailed information.

    If the response validation cause errors, the test fails with
    detailed information.

    Examples:
        >>> from scimpler.validator import ResourceObjectGet
        >>> from scimpler.schemas import UserSchema
        >>>
        >>> response = ...
        >>>
        >>> assert_response(
        >>>     validator=ResourceObjectGet(resource_schema=UserSchema()),
        >>>     status_code=200,
        >>>     headers=response.headers,
        >>>     body=response.json,
        >>> )
    """

    issues = validator.validate_response(status_code=status_code, **kwargs)

    warnings_ = list(issues.warnings)
    if warnings_:
        warnings.warn(
            message=_format(warnings_),
            category=ScimplerCompatibilityWarning,
            stacklevel=2,
        )
    errors = list(issues.errors)
    if errors:
        pytest.fail(f"\n\nErrors:\n{_format(errors)}")


def _format(
    issues: Iterable[tuple[tuple[Union[str, int], ...], list]],
) -> str:
    output = ""
    categories: dict = defaultdict(dict)
    for location, location_issues in issues:
        categories[location[0]][location[1:]] = location_issues

    for category, category_issues in categories.items():
        output += f"\t{category}:\n"
        for location, errors in category_issues.items():
            if location:
                output += f"\t\t{'.'.join(str(part) for part in location)}:\n"
            for error in errors:
                type_ = "error" if isinstance(error, ValidationError) else "warning"
                output += f"\t\t\t{type_}: {error.message} ({error.code})\n"

    return output
