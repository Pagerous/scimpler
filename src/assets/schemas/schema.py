from typing import Any, Optional, Union

from src.container import Missing, SCIMDataContainer
from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    Unknown,
)
from src.data.schemas import BaseResourceSchema, ResourceSchema, SchemaExtension
from src.error import ValidationError, ValidationIssues, ValidationWarning


def validate_attributes(value: list[SCIMDataContainer]) -> ValidationIssues:
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
        elif attr_type == "complex":
            issues.add_warning(
                issue=ValidationWarning.missing(),
                location=(i, "subAttributes"),
            )

        if attr_type == "string" and item.get("caseExact") in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=(i, "caseExact"),
                proceed=False,
            )
    return issues


def serialize_attributes(value: list[SCIMDataContainer]) -> list[SCIMDataContainer]:
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
    description="A complex attribute that includes the attributes of a schema.",
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    validators=[validate_attributes],
    serializer=serialize_attributes,
    sub_attributes=[
        String(
            name="name",
            description="The attribute's name.",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="type",
            description=(
                "The attribute's data type. "
                "Valid values include 'string', 'complex', 'boolean', "
                "'decimal', 'integer', 'dateTime', 'reference'."
            ),
            canonical_values=[
                "string",
                "integer",
                "boolean",
                "reference",
                "dateTime",
                "binary",
                "complex",
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Unknown(
            name="subAttributes",
            description="Used to define the sub-attributes of a complex attribute.",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="multiValued",
            description="A Boolean value indicating an attribute's plurality.",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="description",
            description="A human-readable description of the attribute.",
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="required",
            description="A boolean value indicating whether or not the attribute is required.",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Unknown(
            name="canonicalValues",
            description=(
                "A collection of canonical values.  When "
                "applicable, service providers MUST specify the "
                "canonical types, e.g., 'work', 'home'."
            ),
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        Boolean(
            name="caseExact",
            description=(
                "A Boolean value indicating whether or not a string attribute is case sensitive."
            ),
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="mutability",
            description="Indicates whether or not an attribute is modifiable.",
            canonical_values=["readOnly", "readWrite", "immutable", "writeOnly"],
            restrict_canonical_values=True,
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="returned",
            description="Indicates when an attribute is returned in a response (e.g., to a query).",
            canonical_values=["always", "never", "default", "request"],
            restrict_canonical_values=True,
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="uniqueness",
            description="Indicates how unique a value must be.",
            canonical_values=["none", "server", "global"],
            restrict_canonical_values=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
        String(
            name="referenceTypes",
            description=(
                "Used only with an attribute of type "
                "'reference'.  Specifies a SCIM resourceType that a "
                "reference attribute MAY refer to, e.g., 'User'."
            ),
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            issuer=AttributeIssuer.SERVER,
        ),
    ],
)


class _Schema(BaseResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Schema",
            name="Schema",
            endpoint="/Schemas",
            attrs=[
                String(
                    name="id",
                    description=(
                        "The unique URI of the schema. "
                        "When applicable, service providers MUST specify the URI."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                String(
                    name="name",
                    description=(
                        "The schema's human-readable name.  When "
                        "applicable, service providers MUST specify the name e.g., 'User'."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                String(
                    name="description",
                    description=(
                        "The schema's human-readable description.  When "
                        "applicable, service providers MUST specify the description."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                    issuer=AttributeIssuer.SERVER,
                ),
                attributes,
            ],
        )

    def get_repr(
        self,
        schema: Union[ResourceSchema, SchemaExtension],
        version: Optional[str] = None,
    ) -> dict[str, Any]:
        attrs = schema.attrs if isinstance(schema, SchemaExtension) else schema.attrs.core_attrs
        output = {
            "id": schema.schema,
            "schemas": self.schemas,
            "name": schema.name,
            "description": schema.description,
            "attributes": [attr.to_dict() for attr in attrs],
            "meta": {
                "resourceType": "Schema",
                "location": f"{self.endpoint}/{schema.schema}",
            },
        }
        if version:
            output["meta"]["version"] = version
        return output


Schema = _Schema()
