from src.parser.attributes import type as at
from src.parser.attributes.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    ComplexAttribute,
)
from src.parser.error import ValidationError, ValidationIssues


def bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add(
            issue=ValidationError.reserved_keyword("bulkId"),
            proceed=False,
        )
    return issues


schemas = Attribute(
    name="schemas",
    type_=at.URIReference,
    required=True,
    case_exact=True,
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)


id_ = Attribute(
    name="id",
    type_=at.String,
    required=True,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.SERVER,
    validators=[bulk_id_validator],
)

external_id = Attribute(
    name="externalId",
    type_=at.String,
    required=False,
    issuer=AttributeIssuer.CLIENT,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,  # assumed uniqueness is controlled by clients
)

_meta__resource_type = Attribute(
    name="resourceType",
    type_=at.String,
    required=False,
    case_exact=True,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__created = Attribute(
    name="created",
    type_=at.DateTime,
    required=False,
    case_exact=False,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__last_modified = Attribute(
    name="lastModified",
    type_=at.DateTime,
    required=False,
    case_exact=False,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "Content-Location" HTTP response header
_meta__location = Attribute(
    name="location",
    type_=at.URIReference,
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "ETag" HTTP response header
_meta__version = Attribute(
    name="location",
    type_=at.String,
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


meta = ComplexAttribute(
    sub_attributes=[
        _meta__resource_type,
        _meta__created,
        _meta__last_modified,
        _meta__location,
        _meta__version,
    ],
    name="meta",
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)
