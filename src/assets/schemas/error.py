from src.attributes import AttributeReturn, String
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema


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


class Error(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:Error",
            attrs=[
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
            ],
        )
