from src.assets.schemas import User
from src.assets.schemas.resource_type import ResourceType


def test_resource_type_schema_is_validated():
    schema = ResourceType
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

    assert schema.validate(input_).to_dict(msg=True) == {}


def test_resource_type_representation_can_be_generated():
    expected = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
        "id": "User",
        "name": "User",
        "description": "",
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

    actual = ResourceType.get_repr(User)

    assert actual == expected
