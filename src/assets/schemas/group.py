from src.data.attributes import AttributeMutability, Complex, String, URIReference
from src.data.schemas import ResourceSchema

Group = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:Group",
    name="Group",
    plural_name="Groups",
    endpoint="/Groups",
    description="Group",
    attrs=[
        String(
            name="displayName",
            required=True,
        ),
        Complex(
            sub_attributes=[
                String(
                    name="value",
                    mutability=AttributeMutability.IMMUTABLE,
                ),
                URIReference(
                    name="$ref",
                    mutability=AttributeMutability.IMMUTABLE,
                ),
                String(
                    name="display",
                    mutability=AttributeMutability.IMMUTABLE,
                ),
            ],
            name="members",
            multi_valued=True,
            mutability=AttributeMutability.READ_WRITE,
        ),
    ],
)
