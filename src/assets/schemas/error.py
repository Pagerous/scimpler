from src.data.attributes import (
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    String,
)
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues


def validate_error_status(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        value = int(value)
    except ValueError:
        issues.add_error(
            issue=ValidationError.bad_error_status(),
            proceed=False,
        )
        return issues
    if not 300 <= value < 600:
        issues.add_error(
            issue=ValidationError.bad_error_status(),
            proceed=True,
        )
    return issues


status = String(
    name="status",
    required=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
    validators=[validate_error_status],
)


scim_type = String(
    name="scimType",
    canonical_values=[
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
    ],
    restrict_canonical_values=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)

detail = String(
    name="detail",
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
