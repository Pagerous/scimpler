from scimpler.schemas.resource_type import ResourceTypeSchema
from scimpler.data.attr_presence import AttrPresenceConfig


def test_resource_type_schema_is_validated():
    schema = ResourceTypeSchema()
    input_ = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
        "id": "User",
        "name": "User",
        "endpoint": "/Users",
        "description": "User Account",
        "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
        "schemaExtensions": [
            {
                "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                "required": True,
            }
        ],
        "meta": {
            "location": "https://example.com/v2/ResourceTypes/User",
            "resourceType": "ResourceType",
        },
    }

    assert schema.validate(input_, AttrPresenceConfig("RESPONSE")).to_dict(msg=True) == {}


def test_resource_type_representation_can_be_generated(user_schema):
    expected = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
        "id": "User",
        "name": "User",
        "description": "User Account",
        "endpoint": "/Users",
        "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
        "schemaExtensions": [
            {
                "required": True,
                "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            }
        ],
        "meta": {"location": "/ResourceTypes/User", "resourceType": "ResourceType"},
    }

    actual = ResourceTypeSchema().get_repr(user_schema)

    assert actual == expected
