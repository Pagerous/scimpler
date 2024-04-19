from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    URIReference,
)
from src.data.schemas import ResourceSchema

id_ = String(
    name="id",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


name = String(
    name="name",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


description = String(
    name="description",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


endpoint = URIReference(
    name="endpoint",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


schema = String(
    name="schema",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)


_schema_extensions__schema = schema

_schema_extensions__required = Boolean(
    name="required",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
    required=True,
)

schema_extensions = Complex(
    sub_attributes=[_schema_extensions__schema, _schema_extensions__required],
    name="schemaExtensions",
    multi_valued=True,
)


ResourceType = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:ResourceType",
    attrs=[name, description, endpoint, schema, schema_extensions],
    name="ResourceType",
    attr_overrides={"id": id_},
)
