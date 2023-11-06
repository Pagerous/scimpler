import pytest

from src.parser.attributes.attributes import AttributeName
from src.parser.attributes_presence import AttributePresenceChecker
from src.parser.resource.schemas import USER


@pytest.mark.parametrize(
    ("attr_names", "expected"),
    (
        (["username", "name.familyname"], {}),
        (["bad^attr"], {"bad^attr": {"_errors": [{"code": 111}]}}),
    ),
)
def test_attribute_presence_checker_parsing(attr_names, expected):
    _, issues = AttributePresenceChecker.parse(attr_names, include=True)

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_returned_attribute_that_never_should_be_returned(
    enterprise_user_data,
):
    checker = AttributePresenceChecker()
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

    issues = checker(enterprise_user_data, USER, "RESPONSE")

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(enterprise_user_data):
    checker = AttributePresenceChecker()
    enterprise_user_data["password"] = "1234"

    issues = checker(enterprise_user_data, USER, "REQUEST")

    assert issues.to_dict() == {}


def test_presence_checker_fails_if_returned_attribute_that_was_not_requested():
    checker = AttributePresenceChecker(
        [AttributeName(attr="name", sub_attr="familyName")], include=False
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

    issues = checker(data, USER, "RESPONSE")

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
    }

    issues = checker({}, USER, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_requested_required_attribute():
    checker = AttributePresenceChecker([AttributeName(attr="username")], include=True)
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

    issues = checker(data, USER, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_passes_if_not_provided_requested_optional_attribute():
    checker = AttributePresenceChecker(
        [AttributeName(attr="name", sub_attr="familyname")], include=True
    )
    data = {
        "id": "1",
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }

    issues = checker(data, USER, "RESPONSE")

    assert issues.to_dict() == {}
