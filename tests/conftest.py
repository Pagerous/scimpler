from copy import deepcopy
from typing import Optional

import pytest

from scimpler import registry
from scimpler.config import create_service_provider_config
from scimpler.container import SCIMData
from scimpler.data.attrs import (
    AttrFilter,
    Binary,
    Boolean,
    Complex,
    DateTime,
    Decimal,
    ExternalReference,
    Integer,
    SCIMReference,
    String,
    URIReference,
)
from scimpler.data.patch_path import PatchPath
from scimpler.data.schemas import ResourceSchema
from scimpler.schemas import GroupSchema, UserSchema
from scimpler.schemas.user import EnterpriseUserSchemaExtension


class FakeSchema(ResourceSchema):
    default_attrs = [
        Integer("int"),
        String("str"),
        String("str_cs", case_exact=True),
        String("str_mv", multi_valued=True),
        String("str_cs_mv", case_exact=True, multi_valued=True),
        Boolean("bool"),
        DateTime("datetime"),
        Decimal("decimal"),
        Binary("binary"),
        ExternalReference("external_ref"),
        URIReference("uri_ref"),
        SCIMReference("scim_ref", reference_types=["FakeSchema"]),
        Complex(
            "c",
            sub_attributes=[String("value")],
        ),
        Complex(
            "c_mv",
            sub_attributes=[String("value", multi_valued=True)],
            multi_valued=True,
        ),
        Complex(
            "c2",
            sub_attributes=[String("str"), Integer("int"), Boolean("bool", required=True)],
        ),
        Complex(
            "c2_mv",
            sub_attributes=[
                String("str"),
                Integer("int"),
                Boolean("bool", required=True),
            ],
            multi_valued=True,
        ),
        String("userName", case_exact=True),
        Integer("title"),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(
            schema="schema:for:tests",
            name="FakeSchema",
            plural_name="SchemasForTests",
            endpoint="/SchemasForTests",
            attr_filter=attr_filter,
        )


_user_schema = UserSchema()
_group_schema = GroupSchema()
_enterprise_extension = EnterpriseUserSchemaExtension()
_fake_schema = FakeSchema()


@pytest.fixture(scope="session")
def user_schema() -> UserSchema:
    return _user_schema


@pytest.fixture(scope="session")
def group_schema() -> GroupSchema:
    return _group_schema


@pytest.fixture(scope="session")
def enterprise_extension() -> EnterpriseUserSchemaExtension:
    return _enterprise_extension


@pytest.fixture(scope="session")
def fake_schema() -> "FakeSchema":
    return _fake_schema


@pytest.fixture(scope="session")
def schema(request, user_schema, group_schema, fake_schema):
    if request.param is None:
        return None

    if request.param == "user_schema":
        return user_schema

    if request.param == "group_schema":
        return group_schema

    if request.param == "fake_schema":
        return fake_schema

    raise ValueError("unknown schema")


def pytest_sessionstart(session):
    _user_schema.extend(_enterprise_extension, required=True)
    registry.register_resource_schema(_user_schema)
    registry.register_resource_schema(_group_schema)
    registry.register_resource_schema(_fake_schema)


@pytest.fixture(scope="session", autouse=True)
def set_service_provider_config():
    registry.set_service_provider_config(
        create_service_provider_config(
            patch={"supported": True},
            bulk={"max_operations": 10, "max_payload_size": 4242, "supported": True},
            filter_={"max_results": 100, "supported": True},
            change_password={"supported": True},
            sort={"supported": True},
            etag={"supported": True},
        )
    )


@pytest.fixture
def user_data_client():
    return {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "externalId": "1",
        "userName": "bjensen@example.com",
        "name": {
            "formatted": "Ms. Barbara J Jensen, III",
            "familyName": "Jensen",
            "givenName": "Barbara",
            "middleName": "Jane",
            "honorificPrefix": "Ms.",
            "honorificSuffix": "III",
        },
        "displayName": "Babs Jensen",
        "nickName": "Babs",
        "profileUrl": "https://login.example.com/bjensen",
        "emails": [
            {"value": "bjensen@example.com", "type": "work", "primary": True},
            {"value": "babs@jensen.org", "type": "home"},
        ],
        "addresses": [
            {
                "streetAddress": "100 Universal City Plaza",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "US",
                "formatted": "100 Universal City Plaza\nHollywood, CA 91608 USA",
                "type": "work",
            },
            {
                "streetAddress": "456 Hollywood Blvd",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "US",
                "formatted": "456 Hollywood Blvd\nHollywood, CA 91608 USA",
                "type": "home",
            },
        ],
        "phoneNumbers": [
            {"value": "555-555-5555", "type": "work"},
            {"value": "555-555-4444", "type": "mobile"},
        ],
        "ims": [{"value": "someaimhandle", "type": "aim"}],
        "photos": [
            {"value": "https://photos.example.com/profilephoto/72930000000Ccne/F", "type": "photo"},
            {
                "value": "https://photos.example.com/profilephoto/72930000000Ccne/T",
                "type": "thumbnail",
            },
        ],
        "userType": "Employee",
        "title": "Tour Guide",
        "preferredLanguage": "en-US",
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "active": True,
        "password": "t1meMa$heen",
        "groups": [
            {
                "value": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                "$ref": "../Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "display": "Tour Guides",
            },
            {
                "value": "fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "$ref": "../Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "display": "Employees",
            },
            {
                "value": "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "$ref": "../Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "display": "US Employees",
            },
        ],
        "x509Certificates": [
            {
                "value": (
                    "MIIDQzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjELMAkGA1UEBhMCVVMx"
                    "EzARBgNVBAgMCkNhbGlmb3JuaWExFDASBgNVBAoMC2V4YW1wbGUuY29tMRQwEgYD"
                    "VQQDDAtleGFtcGxlLmNvbTAeFw0xMTEwMjIwNjI0MzFaFw0xMjEwMDQwNjI0MzFa"
                    "MH8xCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRQwEgYDVQQKDAtl"
                    "eGFtcGxlLmNvbTEhMB8GA1UEAwwYTXMuIEJhcmJhcmEgSiBKZW5zZW4gSUlJMSIw"
                    "IAYJKoZIhvcNAQkBFhNiamVuc2VuQGV4YW1wbGUuY29tMIIBIjANBgkqhkiG9w0B"
                    "AQEFAAOCAQ8AMIIBCgKCAQEA7Kr+Dcds/JQ5GwejJFcBIP682X3xpjis56AK02bc"
                    "1FLgzdLI8auoR+cC9/Vrh5t66HkQIOdA4unHh0AaZ4xL5PhVbXIPMB5vAPKpzz5i"
                    "PSi8xO8SL7I7SDhcBVJhqVqr3HgllEG6UClDdHO7nkLuwXq8HcISKkbT5WFTVfFZ"
                    "zidPl8HZ7DhXkZIRtJwBweq4bvm3hM1Os7UQH05ZS6cVDgweKNwdLLrT51ikSQG3"
                    "DYrl+ft781UQRIqxgwqCfXEuDiinPh0kkvIi5jivVu1Z9QiwlYEdRbLJ4zJQBmDr"
                    "SGTMYn4lRc2HgHO4DqB/bnMVorHB0CC6AV1QoFK4GPe1LwIDAQABo3sweTAJBgNV"
                    "HRMEAjAAMCwGCWCGSAGG+EIBDQQfFh1PcGVuU1NMIEdlbmVyYXRlZCBDZXJ0aWZp"
                    "Y2F0ZTAdBgNVHQ4EFgQU8pD0U0vsZIsaA16lL8En8bx0F/gwHwYDVR0jBBgwFoAU"
                    "dGeKitcaF7gnzsNwDx708kqaVt0wDQYJKoZIhvcNAQEFBQADgYEAA81SsFnOdYJt"
                    "Ng5Tcq+/ByEDrBgnusx0jloUhByPMEVkoMZ3J7j1ZgI8rAbOkNngX8+pKfTiDz1R"
                    "C4+dx8oU6Za+4NJXUjlL5CvV6BEYb1+QAEJwitTVvxB/A67g42/vzgAtoRUeDov1"
                    "+GFiBZ+GNF/cAYKcMtGcrs2i97ZkJMo="
                )
            }
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "1",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
        },
    }


@pytest.fixture
def user_data_server(user_data_client):
    data = deepcopy(user_data_client)
    data["id"] = "2819c223-7f76-453a-919d-413861904646"
    data["meta"] = {
        "resourceType": "User",
        "created": "2010-01-23T04:56:22+00:00",
        "lastModified": "2010-01-23T04:56:22+00:00",
        "version": r'W/"3694e05e9dff591"',
        "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    }
    data.pop("password")
    return data


@pytest.fixture
def list_user_data(user_data_server):
    resources = [deepcopy(user_data_server), deepcopy(user_data_server)]
    resources[0]["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]["manager"][
        "displayName"
    ] = "Jan Kowalski"
    resources[1]["id"] = "2819c223-7f76-453a-919d-413861904645"
    resources[1]["externalId"] = "2"
    resources[1]["userName"] = "sven"
    resources[1]["name"]["formatted"] = "Ms. Barbara J Sven III"
    resources[1]["name"]["familyName"] = "Sven"
    resources[1]["emails"] = [
        {
            "value": "sven@example.com",
            "type": "work",
            "primary": True,
        },
        {
            "value": "babs@sven.org",
            "type": "home",
        },
    ]
    resources[1]["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]["employeeNumber"] = (
        "2"
    )
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponseSchema"],
        "totalResults": 2,
        "startIndex": 1,
        "itemsPerPage": 2,
        "Resources": resources,
    }


@pytest.fixture
def list_data(list_user_data):
    data = list_user_data.copy()
    data["Resources"].append(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
            "displayName": "Tour Guides",
            "members": [
                {
                    "value": "2819c223-7f76-453a-919d-413861904646",
                    "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                    "type": "User",
                },
                {
                    "value": "902c246b-6245-4190-8e05-00816be7344a",
                    "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
                    "type": "User",
                },
            ],
            "meta": {
                "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "resourceType": "Group",
                "created": "2011-05-13T04:42:34+00:00",
                "lastModified": "2011-05-13T04:42:34+00:00",
                "version": 'W/"3694e05e9dff594"',
            },
        }
    )
    data["totalResults"] = 3
    data["itemsPerPage"] = 3
    return data


@pytest.fixture
def error_data():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "400",
        "scimType": "tooMany",
        "detail": "you did wrong, bro",
    }


@pytest.fixture
def bulk_request_serialized():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequestSchema"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {
                    "schemas": [
                        "urn:ietf:params:scim:schemas:core:2.0:User",
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    ],
                    "userName": "Alice",
                },
            },
            {
                "method": "PUT",
                "path": "/Users/b7c14771-226c-4d05-8860-134711653041",
                "version": 'W/"3694e05e9dff591"',
                "data": {
                    "schemas": [
                        "urn:ietf:params:scim:schemas:core:2.0:User",
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    ],
                    "id": "b7c14771-226c-4d05-8860-134711653041",
                    "userName": "Bob",
                },
            },
            {
                "method": "PATCH",
                "path": "/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc",
                "version": 'W"edac3253e2c0ef2"',
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {"op": "remove", "path": "nickName"},
                        {"op": "add", "path": "userName", "value": "Dave"},
                    ],
                },
            },
            {
                "method": "DELETE",
                "path": "/Users/e9025315-6bea-44e1-899c-1e07454e468b",
                "version": 'W/"0ee8add0a938e1a"',
            },
        ],
    }


@pytest.fixture
def bulk_request_deserialized(bulk_request_serialized: dict):
    deserialized: dict = deepcopy(bulk_request_serialized)
    deserialized["Operations"][2]["data"]["Operations"][0]["path"] = PatchPath.deserialize(
        deserialized["Operations"][2]["data"]["Operations"][0]["path"]
    )
    deserialized["Operations"][2]["data"]["Operations"][1]["path"] = PatchPath.deserialize(
        deserialized["Operations"][2]["data"]["Operations"][1]["path"]
    )
    return SCIMData(deserialized)


@pytest.fixture
def group_data_server():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
        "displayName": "Tour Guides",
        "members": [
            {
                "value": "2819c223-7f76-453a-919d-413861904646",
                "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "type": "User",
            },
            {
                "value": "902c246b-6245-4190-8e05-00816be7344a",
                "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
                "type": "User",
            },
        ],
        "meta": {
            "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
            "resourceType": "Group",
            "created": "2011-05-13T04:42:34+00:00",
            "lastModified": "2011-05-13T04:42:34+00:00",
            "version": 'W/"3694e05e9dff594"',
        },
    }


CONFIG = create_service_provider_config(
    patch={"supported": True},
    bulk={"max_operations": 10, "max_payload_size": 4242, "supported": True},
    filter_={"max_results": 100, "supported": True},
    change_password={"supported": True},
    sort={"supported": True},
    etag={"supported": True},
)
