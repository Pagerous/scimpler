from ..attributes import type as at
from ..error import ValidationError, ValidationIssues
from .attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    ComplexAttribute,
)


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
    issuer=AttributeIssuer.BOTH,
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
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=True,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.SERVER,
    validators=[bulk_id_validator],
)

external_id = Attribute(
    name="externalId",
    issuer=AttributeIssuer.PROVISIONING_CLIENT,
    type_=at.String,
    required=False,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,  # assumed uniqueness is controlled by clients
)

_meta__resource_type = Attribute(
    name="resourceType",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=False,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__created = Attribute(
    name="created",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.DateTime,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__last_modified = Attribute(
    name="lastModified",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.DateTime,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "Content-Location" HTTP response header
_meta__location = Attribute(
    name="location",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.URIReference,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "ETag" HTTP response header
_meta__version = Attribute(
    name="location",
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    type_=at.String,
    required=False,
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
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    required=False,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)
