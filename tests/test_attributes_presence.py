from datetime import datetime

import pytest

from src.attributes_presence import AttributePresenceChecker
from src.data.container import AttrRep, SCIMDataContainer
from src.resource.schemas.user import User


@pytest.mark.parametrize(
    ("attr_reps", "expected"),
    (
        (["username", "name.familyname"], {}),
        (["bad^attr"], {"bad^attr": {"_errors": [{"code": 111}]}}),
    ),
)
def test_attribute_presence_checker_parsing(attr_reps, expected):
    _, issues = AttributePresenceChecker.parse(attr_reps, include=True)

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_returned_attribute_that_never_should_be_returned(
    user_data_dump,
):
    checker = AttributePresenceChecker()
    user_data_dump["password"] = "1234"
    expected = {
        "password": {
            "_errors": [
                {
                    "code": 19,
                }
            ]
        }
    }

    issues = checker(SCIMDataContainer(user_data_dump), User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(user_data_parse):
    checker = AttributePresenceChecker(ignore_required=[AttrRep(attr="id")])
    user_data_parse["password"] = "1234"

    issues = checker(SCIMDataContainer(user_data_parse), User().attrs, "REQUEST")

    assert issues.to_dict() == {}


def test_presence_checker_fails_on_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker([AttrRep(attr="name")], include=False)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {"name": {"_errors": [{"code": 19}]}}

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker([AttrRep(attr="name")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
            "meta": {
                "resourceType": "User",
                "created": datetime(2011, 8, 1, 18, 29, 49),
                "lastModified": datetime(2011, 8, 1, 18, 29, 49),
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

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_sub_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker([AttrRep(attr="name", sub_attr="familyName")], include=False)
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

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_sub_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker([AttrRep(attr="name", sub_attr="familyName")], include=True)
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

    issues = checker(data, User().attrs, "RESPONSE")

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

    issues = checker(SCIMDataContainer(), User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_if_not_provided_requested_required_attribute():
    checker = AttributePresenceChecker([AttrRep(attr="username")], include=True)
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

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_passes_if_not_provided_requested_optional_attribute():
    checker = AttributePresenceChecker([AttrRep(attr="name", sub_attr="familyname")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == {}


def test_presence_checker_fails_on_multivalued_complex_attr_not_requested_by_exclusion():
    checker = AttributePresenceChecker([AttrRep(attr="emails", sub_attr="display")], include=False)
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

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_checker_fails_on_multivalued_complex_attr_not_requested_by_inclusion():
    checker = AttributePresenceChecker([AttrRep(attr="emails", sub_attr="display")], include=True)
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

    issues = checker(data, User().attrs, "RESPONSE")

    assert issues.to_dict() == expected
