from typing import Optional

from src.data.attrs import (
    Attribute,
    AttributeMutability,
    Complex,
    SCIMReference,
    String,
)
from src.data.schemas import AttrFilter, ResourceSchema


class GroupSchema(ResourceSchema):
    default_attrs: list[Attribute] = [
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
                SCIMReference(
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

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Group",
            name="Group",
            plural_name="Groups",
            endpoint="/Groups",
            description="Group",
            attr_filter=attr_filter,
        )
