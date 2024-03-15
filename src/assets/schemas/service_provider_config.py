from copy import deepcopy

from src.data import type as type_
from src.data.attributes import Attribute, AttributeMutability, ComplexAttribute
from src.data.schemas import ResourceSchema, id_

id_ = deepcopy(id_)
id_._required = False

documentation_uri = Attribute(
    name="documentationUri",
    type_=type_.ExternalReference,
    mutability=AttributeMutability.READ_ONLY,
)

_supported = Attribute(
    name="supported",
    type_=type_.Boolean,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

patch = ComplexAttribute(
    sub_attributes=[_supported],
    name="patch",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_bulk_max_operations = Attribute(
    name="maxOperations",
    type_=type_.Integer,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_bulk_max_payload_size = Attribute(
    name="maxPayloadSize",
    type_=type_.Integer,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

bulk = ComplexAttribute(
    sub_attributes=[_supported, _bulk_max_operations, _bulk_max_payload_size],
    name="bulk",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_filter_max_results = Attribute(
    name="maxResults",
    type_=type_.Integer,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

filter_ = ComplexAttribute(
    sub_attributes=[_supported, _filter_max_results],
    name="filter",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


change_password = ComplexAttribute(
    sub_attributes=[_supported],
    name="changePassword",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


sort = ComplexAttribute(
    sub_attributes=[_supported],
    name="sort",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


etag = ComplexAttribute(
    sub_attributes=[_supported],
    name="etag",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)


_authentication_schemes_type = Attribute(
    name="type",
    type_=type_.String,
    required=True,
    canonical_values=["oauth", "oauth2", "oauthbearertoken", "httpbasic", "httpdigest"],
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_name = Attribute(
    name="name",
    type_=type_.String,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_description = Attribute(
    name="description",
    type_=type_.String,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_spec_uri = Attribute(
    name="specUri",
    type_=type_.ExternalReference,
    mutability=AttributeMutability.READ_ONLY,
)

_authentication_schemes_documentation_uri = Attribute(
    name="specUri",
    type_=type_.ExternalReference,
    mutability=AttributeMutability.READ_ONLY,
)

authentication_schemes = ComplexAttribute(
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


class ServiceProviderConfig(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig",
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
            name="ServiceProviderConfig",
            attr_overrides={"id": id_},
        )
