from src.data import type as type_
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    ComplexAttribute,
)
from src.data.schemas import ResourceSchema

id_ = Attribute(
    name="id",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


name = Attribute(
    name="name",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


description = Attribute(
    name="description",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


endpoint = Attribute(
    name="endpoint",
    type_=type_.URIReference,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


schema = Attribute(
    name="schema",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


_schema_extensions__schema = schema

_schema_extensions__required = Attribute(
    name="required",
    type_=type_.Boolean,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)

schema_extensions = ComplexAttribute(
    sub_attributes=[_schema_extensions__schema, _schema_extensions__required],
    name="schemaExtensions",
    multi_valued=True,
)


class ResourceType(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:ResourceType",
            attrs=[name, description, endpoint, schema, schema_extensions],
            name="ResourceType",
            attr_overrides={"id": id_},
        )
