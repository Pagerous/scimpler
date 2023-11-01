import pytest

from src.parser.attributes.attributes import AttributeName
from src.parser.parameters.attributes_presence import AttributePresenceChecker
from src.parser.resource.schemas import USER


@pytest.mark.parametrize(
    ("attr_names", "schema", "expected"),
    (
        (["username"], USER, {}),
        (["username", "name.familyname"], USER, {}),
        (["bad^attr"], None, {"bad^attr": {"_errors": [{"code": 111}]}}),
        (["bad^attr"], USER, {"bad^attr": {"_errors": [{"code": 111}, {"code": 200}]}}),
        (["non.existing"], USER, {"non": {"existing": {"_errors": [{"code": 200}]}}}),
        (["non.existing"], None, {}),
    ),
)
def test_attribute_presence_checker_parsing(attr_names, schema, expected):
    _, issues = AttributePresenceChecker.parse(attr_names, include=True, schema=schema)

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_returned_attribute_that_never_should_be_returned(
    enterprise_user_data,
):
    checker = AttributePresenceChecker(schema=USER)
    enterprise_user_data["password"] = "1234"
    expected = {
        "password": {
            "_errors": [
                {
                    "code": 19,
                }
            ]
        }
    }

    issues = checker(enterprise_user_data, "RESPONSE")

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(enterprise_user_data):
    checker = AttributePresenceChecker(schema=USER)
    enterprise_user_data["password"] = "1234"

    issues = checker(enterprise_user_data, "REQUEST")

    assert issues.to_dict() == {}


def test_presence_checker_fails_if_returned_attribute_that_was_not_requested():
    checker = AttributePresenceChecker(
        [AttributeName(attr="name", sub_attr="familyName")], include=False, schema=USER
    )
    data = {
        "id": "1",
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "Pagerous",
        "name": {
            "familyName": "Pajor",
        },
    }

    expected = {
        "name": {
            "familyname": {
                "_errors": [
                    {
                        "code": 19,
                    }
                ]
            }
        }
    }

    issues = checker(data, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_attribute_that_always_should_be_returned():
    checker = AttributePresenceChecker(schema=USER)

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
    }

    issues = checker({}, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_requested_required_attribute():
    checker = AttributePresenceChecker([AttributeName(attr="username")], include=True, schema=USER)
    data = {
        "id": "1",
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }
    expected = {
        "username": {
            "_errors": [
                {
                    "code": 15,
                }
            ]
        },
    }

    issues = checker(data, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_passes_if_not_provided_requested_optional_attribute():
    checker = AttributePresenceChecker(
        [AttributeName(attr="name", sub_attr="familyname")], include=True, schema=USER
    )
    data = {
        "id": "1",
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }

    issues = checker(data, "RESPONSE")

    assert issues.to_dict() == {}
