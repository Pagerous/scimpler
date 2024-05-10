from src.assets.schemas.user import User
from src.attributes import Integer
from src.attributes_presence import AttributePresenceChecker
from src.container import BoundedAttrRep, SCIMDataContainer
from src.schemas import ResourceSchema, SchemaExtension


def test_presence_checker_fails_if_returned_attribute_that_never_should_be_returned(
    user_data_server,
):
    checker = AttributePresenceChecker()
    user_data_server["password"] = "1234"
    expected = {
        "password": {
            "_errors": [
                {
                    "code": 19,
                }
            ]
        }
    }

    issues = checker(SCIMDataContainer(user_data_server), User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(user_data_client):
    checker = AttributePresenceChecker()
    user_data_client["password"] = "1234"

    issues = checker(SCIMDataContainer(user_data_client), User.attrs, "REQUEST")

    assert issues.to_dict(msg=True) == {}


def test_presence_checker_fails_on_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker([BoundedAttrRep(attr="name")], include=False)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {"name": {"_errors": [{"code": 19}]}}

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker([BoundedAttrRep(attr="name")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
            "meta": {
                "resourceType": "User",
                "created": "2011-05-13T04:42:34Z",
                "lastModified": "2011-05-13T04:42:34Z",
                "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "version": r"W\/\"f250dd84f0671c3\"",
            },
        }
    )
    expected = {
        "meta": {
            "_errors": [{"code": 19}],
            "resourceType": {"_errors": [{"code": 19}]},
            "created": {"_errors": [{"code": 19}]},
            "lastModified": {"_errors": [{"code": 19}]},
            "location": {"_errors": [{"code": 19}]},
            "version": {"_errors": [{"code": 19}]},
        }
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_sub_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker(
        [BoundedAttrRep(attr="name", sub_attr="familyName")], include=False
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {
        "name": {
            "familyName": {
                "_errors": [
                    {
                        "code": 19,
                    }
                ]
            }
        }
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_sub_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker(
        [BoundedAttrRep(attr="name", sub_attr="familyName")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"familyName": "Pajor", "givenName": "Arkadiusz"},
        }
    )

    expected = {
        "name": {
            "givenName": {
                "_errors": [
                    {
                        "code": 19,
                    }
                ]
            }
        }
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_attribute_that_always_should_be_returned():
    checker = AttributePresenceChecker()

    expected = {
        "id": {
            "_errors": [
                {
                    "code": 15,
                }
            ]
        },
        "schemas": {
            "_errors": [
                {
                    "code": 15,
                }
            ]
        },
        "userName": {
            "_errors": [
                {
                    "code": 15,
                }
            ]
        },
    }

    issues = checker(SCIMDataContainer(), User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_requested_required_attribute():
    checker = AttributePresenceChecker([BoundedAttrRep(attr="username")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )
    expected = {
        "userName": {
            "_errors": [
                {
                    "code": 15,
                }
            ]
        },
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_passes_if_not_provided_requested_optional_attribute():
    checker = AttributePresenceChecker(
        [BoundedAttrRep(attr="name", sub_attr="familyname")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict(msg=True) == {}


def test_presence_checker_fails_on_multivalued_complex_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker(
        [BoundedAttrRep(attr="emails", sub_attr="display")], include=False
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"type": "home", "primary": False},
                {"type": "school", "primary": False, "display": "example@example.com"},
            ],
        }
    )

    expected = {
        "emails": {
            "0": {"display": {"_errors": [{"code": 19}]}},
            "2": {"display": {"_errors": [{"code": 19}]}},
        }
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_multivalued_complex_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker(
        [BoundedAttrRep(attr="emails", sub_attr="display")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"display": "example@example.com"},
                {"type": "school", "primary": False, "display": "example@example.com"},
            ],
        }
    )

    expected = {
        "emails": {
            "0": {"type": {"_errors": [{"code": 19}]}, "primary": {"_errors": [{"code": 19}]}},
            "2": {"type": {"_errors": [{"code": 19}]}, "primary": {"_errors": [{"code": 19}]}},
        }
    }

    issues = checker(data, User.attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_specifying_attribute_issued_by_service_provider_causes_validation_failure(
    user_data_client,
):
    checker = AttributePresenceChecker()
    user_data_client["id"] = "should-not-be-provided"
    expected_issues = {"id": {"_errors": [{"code": 18}]}}

    issues = checker(SCIMDataContainer(user_data_client), User.attrs, "REQUEST")

    assert issues.to_dict() == expected_issues


def test_presence_validation_fails_if_missing_required_field_from_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=True)
    checker = AttributePresenceChecker()
    expected_issues = {"age": {"_errors": [{"code": 15}]}}

    issues = checker(
        SCIMDataContainer({"id": "1", "schemas": ["my:schema"]}), schema.attrs, "RESPONSE"
    )

    assert issues.to_dict() == expected_issues


def test_presence_validation_succeeds_if_missing_required_field_from_non_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=False)
    checker = AttributePresenceChecker()

    issues = checker(
        SCIMDataContainer({"id": "1", "schemas": ["my:schema"]}), schema.attrs, "RESPONSE"
    )

    assert issues.to_dict(msg=True) == {}
