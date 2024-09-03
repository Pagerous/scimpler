from scimpler.data.attrs import (
    Attribute,
    AttributeMutability,
    Complex,
    ScimReference,
    String,
)
from scimpler.data.schemas import ResourceSchema


class GroupSchema(ResourceSchema):
    schema = "urn:ietf:params:scim:schemas:core:2.0:Group"
    name = "Group"
    plural_name = "Groups"
    endpoint = "/Groups"
    description = "Group"
    base_attrs: list[Attribute] = [
        String(
            name="displayName",
            description="A human-readable name for the Group.",
            required=True,
        ),
        Complex(
            name="members",
            multi_valued=True,
            description="A list of members of the Group.",
            sub_attributes=[
                String(
                    name="value",
                    description="Identifier of the member of this Group.",
                    mutability=AttributeMutability.IMMUTABLE,
                ),
                ScimReference(
                    name="$ref",
                    description=(
                        "The URI corresponding to a SCIM resource "
                        "that is a member of this Group."
                    ),
                    reference_types=["User", "Group"],
                    mutability=AttributeMutability.IMMUTABLE,
                ),
                String(
                    name="type",
                    description="A label indicating the type of resource, e.g., 'User' or 'Group'.",
                    canonical_values=["User", "Group"],
                    restrict_canonical_values=True,
                    mutability=AttributeMutability.IMMUTABLE,
                ),
            ],
        ),
    ]
