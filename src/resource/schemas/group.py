from src.data import type as type_
from src.data.attributes import Attribute, AttributeMutability, ComplexAttribute
from src.schemas import ResourceSchema

display_name = Attribute(
    name="displayName",
    type_=type_.String,
    required=True,
)

_members_value = Attribute(
    name="value",
    type_=type_.String,
    mutability=AttributeMutability.IMMUTABLE,
)

_members_ref = Attribute(
    name="$ref",
    type_=type_.URIReference,
    mutability=AttributeMutability.IMMUTABLE,
)

_members_display = Attribute(
    name="display",
    type_=type_.String,
    mutability=AttributeMutability.IMMUTABLE,
)

members = ComplexAttribute(
    sub_attributes=[_members_value, _members_ref, _members_display],
    name="members",
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
)


class Group(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Group",
            attrs=[display_name, members],
            name="Group",
            plural_name="Groups",
        )
