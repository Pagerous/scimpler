from typing import Tuple, Union

from src.data import type as type_
from src.data.attributes import (
    Attribute,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
)
from src.data.container import Invalid
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema


def parse_error_status(value: str) -> Tuple[Union[Invalid, int], ValidationIssues]:
    issues = ValidationIssues()
    try:
        value = int(value)
    except ValueError:
        issues.add(
            issue=ValidationError.bad_error_status(value),
            proceed=False,
        )
        return Invalid, issues
    if not 300 <= value < 600:
        issues.add(
            issue=ValidationError.bad_error_status(value),
            proceed=True,
        )
    return value, issues


def validate_error_scim_type(value: str) -> Tuple[Union[Invalid, str], ValidationIssues]:
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
        return Invalid, issues
    return value, issues


status = Attribute(
    name="status",
    type_=type_.String,
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
    type_=type_.String,
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
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)


class Error(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:Error",
            attrs=[
                status,
                scim_type,
                detail,
            ],
        )

    def __repr__(self) -> str:
        return "Error"
