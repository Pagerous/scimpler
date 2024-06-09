from src.data.attrs import AttributeReturn, String
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues


def validate_error_status(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        value = int(value)
    except ValueError:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=False,
        )
        return issues
    if not 400 <= value < 600:
        issues.add_error(
            issue=ValidationError.bad_error_status(),
            proceed=True,
        )
    return issues


class ErrorSchema(BaseSchema):
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


Error = ErrorSchema()
