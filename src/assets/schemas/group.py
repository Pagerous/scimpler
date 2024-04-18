from src.data.attributes import AttributeMutability, Complex, String, URIReference
from src.data.schemas import ResourceSchema

display_name = String(
    name="displayName",
    required=True,
)

_members_value = String(
    name="value",
    mutability=AttributeMutability.IMMUTABLE,
)

_members_ref = URIReference(
    name="$ref",
    mutability=AttributeMutability.IMMUTABLE,
)

_members_display = String(
    name="display",
    mutability=AttributeMutability.IMMUTABLE,
)

members = Complex(
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
