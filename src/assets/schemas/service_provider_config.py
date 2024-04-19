from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    Boolean,
    Complex,
    ExternalReference,
    Integer,
    String,
)
from src.data.schemas import ResourceSchema, bulk_id_validator

id_ = String(
    name="id",
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.SERVER,
    validators=[bulk_id_validator],
)

documentation_uri = ExternalReference(
    name="documentationUri",
    mutability=AttributeMutability.READ_ONLY,
)

_supported = Boolean(
    name="supported",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

patch = Complex(
    sub_attributes=[_supported],
    name="patch",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_bulk_max_operations = Integer(
    name="maxOperations",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_bulk_max_payload_size = Integer(
    name="maxPayloadSize",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

bulk = Complex(
    sub_attributes=[_supported, _bulk_max_operations, _bulk_max_payload_size],
    name="bulk",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_filter_max_results = Integer(
    name="maxResults",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

filter_ = Complex(
    sub_attributes=[_supported, _filter_max_results],
    name="filter",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


change_password = Complex(
    sub_attributes=[_supported],
    name="changePassword",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


sort = Complex(
    sub_attributes=[_supported],
    name="sort",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


etag = Complex(
    sub_attributes=[_supported],
    name="etag",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_authentication_schemes_type = String(
    name="type",
    required=True,
    canonical_values=["oauth", "oauth2", "oauthbearertoken", "httpbasic", "httpdigest"],
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_name = String(
    name="name",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_description = String(
    name="description",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_spec_uri = ExternalReference(
    name="specUri",
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_documentation_uri = ExternalReference(
    name="specUri",
    mutability=AttributeMutability.READ_ONLY,
)

authentication_schemes = Complex(
    sub_attributes=[
        _authentication_schemes_type,
        _authentication_schemes_name,
        _authentication_schemes_description,
        _authentication_schemes_spec_uri,
        _authentication_schemes_documentation_uri,
    ],
    name="authenticationSchemes",
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    required=True,
)


ServiceProviderConfig = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig",
    name="ServiceProviderConfig",
    endpoint="/ServiceProviderConfig",
    attrs=[
        documentation_uri,
        patch,
        bulk,
        filter_,
        change_password,
        sort,
        etag,
        authentication_schemes,
    ],
    attr_overrides={"id": id_},
)
