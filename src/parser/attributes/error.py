from typing import List

from .attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
)
from src.parser.attributes import type as at
from ..error import ValidationError


def validate_error_status(value: str) -> List[ValidationError]:
    try:
        value = int(value)
    except ValueError:
        return [ValidationError.bad_error_status(value)]
    if not 300 <= value < 600:
        return [ValidationError.bad_error_status(value)]
    return []


def validate_error_scim_type(value: str) -> List[ValidationError]:
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
        "sensitive"
    ]
    if value not in scim_types:
        return [ValidationError.must_be_one_of(scim_types, value)]


status = Attribute(
    name="status",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=True,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
    validators=[validate_error_status],
)


scim_type = Attribute(
    name="scimType",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
    validators=[validate_error_scim_type],
)

detail = Attribute(
    name="detail",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)

