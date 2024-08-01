from typing import Optional

from scimpler.data.attrs import Attribute, AttributeReturn, String
from scimpler.data.schemas import AttrFilter, BaseSchema
from scimpler.error import ValidationError, ValidationIssues


def validate_error_status(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        value_int = int(value)
    except ValueError:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=False,
        )
        return issues
    if not 400 <= value_int < 600:
        issues.add_error(
            issue=ValidationError.bad_value_content(),
            proceed=True,
        )
    return issues


class ErrorSchema(BaseSchema):
    default_attrs: list[Attribute] = [
        String(
            name="status",
            required=True,
            returned=AttributeReturn.ALWAYS,
            validators=[validate_error_status],
        ),
        String(
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
            returned=AttributeReturn.ALWAYS,
        ),
        String(
            name="detail",
            returned=AttributeReturn.ALWAYS,
        ),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:Error",
            attr_filter=attr_filter,
        )
