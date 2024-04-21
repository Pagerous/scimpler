from typing import Any, Dict, List, Union

from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    Unknown,
)
from src.data.container import Missing, SCIMDataContainer
from src.data.schemas import ResourceSchema, SchemaExtension, ServiceResourceSchema
from src.error import ValidationError, ValidationIssues


def validate_attributes(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        attr_type = item.get("type")
        sub_attributes = item.get("subAttributes")
        if sub_attributes not in [Missing, None]:
            if attr_type == "complex":
                issues.merge(
                    attributes.validate(sub_attributes),
                    location=(i, "subAttributes"),
                )
        if attr_type == "string" and item.get("caseExact") in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=(i, "caseExact"),
                proceed=False,
            )
    return issues


def serialize_attributes(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    for i, item in enumerate(value):
        attr_type = item.get("type")
        sub_attributes = item.get("subAttributes")
        if sub_attributes not in [Missing, None]:
            if attr_type != "complex":
                item.pop("subAttributes")
            else:
                item.set("subAttributes", attributes.serialize(sub_attributes))
        if attr_type != "string":
            item.pop("caseExact")
    return value


attributes = Complex(
    name="attributes",
    sub_attributes=[
        String(
            name="name",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="type",
            canonical_values=[
                "string",
                "integer",
                "boolean",
                "reference",
                "dateTime",
                "binary",
                "complex",
            ],
            restrict_canonical_values=False,
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Unknown(
            name="subAttributes",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="multiValued",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="description",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="required",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Unknown(
            name="canonicalValues",
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="caseExact",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="mutability",
            canonical_values=["readOnly", "readWrite", "immutable", "writeOnly"],
            restrict_canonical_values=True,
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="returned",
            canonical_values=["always", "never", "default", "request"],
            restrict_canonical_values=True,
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="uniqueness",
            canonical_values=["none", "server", "global"],
            restrict_canonical_values=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="referenceTypes",
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
    ],
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    validators=[validate_attributes],
    serializeer=serialize_attributes,
)


class _Schema(ServiceResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Schema",
            name="Schema",
            endpoint="/Schemas",
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
                ),
                String(
                    name="description",
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                attributes,
            ],
        )

    def get_repr(self, schema: Union[ResourceSchema, SchemaExtension]) -> Dict[str, Any]:
        return {
            "id": schema.schema,
            "schemas": self.schemas,
            "name": schema.name,
            "description": schema.description,
            "attributes": [attr.to_dict() for attr in schema.attrs.top_level],
            "meta": {
                "resourceType": "Schema",
                "location": f"{self.endpoint}/{schema.schema}",
            },
        }


Schema = _Schema()
