from typing import Optional, Tuple

from src.attributes import type as at
from src.attributes.attributes import (
    Attribute,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
)
from src.error import ValidationError, ValidationIssues


def parse_error_status(value: str) -> Tuple[Optional[int], ValidationIssues]:
    issues = ValidationIssues()
    try:
        value = int(value)
    except ValueError:
        issues.add(
            issue=ValidationError.bad_error_status(value),
            proceed=False,
        )
        return None, issues
    if not 300 <= value < 600:
        issues.add(
            issue=ValidationError.bad_error_status(value),
            proceed=True,
        )
    return value, issues


def validate_error_scim_type(value: str) -> Tuple[Optional[str], ValidationIssues]:
    scim_types = [
        "invalidFilter",
        "tooMany",
        "uniqueness",
        "mutability",
        "invalidSyntax",
        "invalidPath",
        "noTarget",
        "invalidValue",
        "invalidVers",
        "sensitive",
    ]
    issues = ValidationIssues()
    if value not in scim_types:
        issues.add(
            issue=ValidationError.must_be_one_of(scim_types, value),
            proceed=False,
        )
        return None, issues
    return value, issues


status = Attribute(
    name="status",
    type_=at.String,
    required=True,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
    parsers=[parse_error_status],
)


scim_type = Attribute(
    name="scimType",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
    parsers=[validate_error_scim_type],
    dumpers=[validate_error_scim_type],
)

detail = Attribute(
    name="detail",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)
