from typing import Any, Dict

from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    URIReference,
)
from src.data.schemas import ResourceSchema, ServiceResourceSchema


class _ResourceType(ServiceResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:ResourceType",
            name="ResourceType",
            endpoint="/ResourceTypes",
            attrs=[
                String(
                    name="id",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                String(
                    name="name",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                    required=True,
                ),
                String(
                    name="description",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                URIReference(
                    name="endpoint",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                    required=True,
                ),
                String(
                    name="schema",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                    required=True,
                ),
                Complex(
                    sub_attributes=[
                        String(
                            name="schema",
                            mutability=AttributeMutability.READ_ONLY,
                            issuer=AttributeIssuer.SERVER,
                            required=True,
                        ),
                        Boolean(
                            name="required",
                            mutability=AttributeMutability.READ_ONLY,
                            issuer=AttributeIssuer.SERVER,
                            required=True,
                        ),
                    ],
                    name="schemaExtensions",
                    multi_valued=True,
                ),
            ],
        )

    def get_repr(self, schema: ResourceSchema) -> Dict[str, Any]:
        return {
            "schemas": self.schemas,
            "id": schema.name,
            "name": schema.name,
            "endpoint": schema.endpoint,
            "description": schema.description,
            "schema": schema.schema,
            "schemaExtensions": [
                {
                    "schema": extension.schema,
                    "required": required,
                }
                for extension, required in schema.extensions.items()
            ],
            "meta": {
                "location": f"{self.endpoint}/{schema.name}",
                "resourceType": self.name,
            },
        }


ResourceType = _ResourceType()
