from typing import Any

from scimpler.data.attrs import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    UriReference,
)
from scimpler.data.schemas import BaseResourceSchema, ResourceSchema


class ResourceTypeSchema(BaseResourceSchema):
    """
    ResourceType schema, identified by `urn:ietf:params:scim:schemas:core:2.0:ResourceType` URI.

    The default endpoint is `/ResourceTypes`.
    """

    schema = "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
    name = "ResourceType"
    endpoint = "/ResourceTypes"
    base_attrs = [
        String(
            name="id",
            description=(
                "The resource type's server unique id. May be the same as the 'name' attribute."
            ),
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
        ),
        String(
            name="name",
            description=(
                "The resource type name.  When applicable, "
                "service providers MUST specify the name, e.g., 'User'."
            ),
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            required=True,
        ),
        String(
            name="description",
            description=(
                "The resource type's human-readable "
                "description. When applicable, service providers MUST "
                "specify the description."
            ),
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
        ),
        UriReference(
            name="endpoint",
            description=(
                "The resource type's HTTP-addressable "
                "endpoint relative to the Base URL, e.g., '/Users'."
            ),
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            required=True,
        ),
        String(
            name="schema",
            description="The resource type's primary/base schema URI.",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            required=True,
        ),
        Complex(
            name="schemaExtensions",
            multi_valued=True,
            description="A list of URIs of the resource type's schema extensions.",
            sub_attributes=[
                UriReference(
                    name="schema",
                    description="The URI of a schema extension.",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    required=True,
                ),
                Boolean(
                    name="required",
                    description=(
                        "A Boolean value that specifies whether "
                        "or not the schema extension is required for the "
                        "resource type.If true, a resource of this type MUST "
                        "include this schema extension and also include any "
                        "attributes declared as required in this schema extension. "
                        "If false, a resource of this type MAY omit this schema "
                        "extension."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    required=True,
                ),
            ],
        ),
    ]

    def get_repr(self, schema: ResourceSchema) -> dict[str, Any]:
        """
        Returns the representation of the provided resource `schema`, compatible with the
        content returned through `/ResourceTypes` endpoint.
        """
        return {
            "schemas": self.schemas,
            "id": schema.name,
            "name": schema.name,
            "endpoint": schema.endpoint,
            "description": schema.description,
            "schema": schema.schema,
            "schemaExtensions": [
                {
                    "schema": schema,
                    "required": required,
                }
                for schema, required in schema.extensions.items()
            ],
            "meta": {
                "location": f"{self.endpoint}/{schema.name}",
                "resourceType": self.name,
            },
        }
