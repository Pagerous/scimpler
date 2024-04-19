import pytest

from src.assets.schemas import list_response, user
from src.data.container import SCIMDataContainer


def test_validate_items_per_page_consistency__fails_if_not_matching_resources(list_user_data):
    expected = {
        "itemsPerPage": {"_errors": [{"code": 11}]},
        "Resources": {"_errors": [{"code": 11}]},
    }

    issues = list_response.validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=1,
    )

    assert issues.to_dict() == expected


def test_validate_items_per_page_consistency__succeeds_if_correct_data(list_user_data):
    issues = list_response.validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=2,
    )

    assert issues.to_dict(msg=True) == {}


def test_resources_validation_fails_if_bad_type(list_user_data):
    schema = list_response.ListResponse([user.User])
    list_user_data["Resources"][0]["userName"] = 123
    list_user_data["Resources"][1]["userName"] = 123

    expected_issues = {
        "Resources": {
            "0": {"userName": {"_errors": [{"code": 2}]}},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        }
    }

    issues = schema.validate(list_user_data)

    assert issues.to_dict() == expected_issues


def test_resources_validation_succeeds_for_correct_data(list_user_data):
    schema = list_response.ListResponse([user.User])
    # below fields should be filtered-out
    list_user_data["unexpected"] = 123
    list_user_data["Resources"][0]["unexpected"] = 123
    list_user_data["Resources"][1]["name"]["unexpected"] = 123

    issues = schema.validate(list_user_data)

    assert issues.to_dict(msg=True) == {}


def test_resources_validation_fails_if_bad_resource_type(list_user_data):
    schema = list_response.ListResponse([user.User])
    list_user_data["Resources"][0] = []
    list_user_data["Resources"][1]["userName"] = 123
    expected = {
        "Resources": {
            "0": {"_errors": [{"code": 2}]},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        }
    }

    issues = schema.validate(list_user_data)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (
            [
                SCIMDataContainer(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                # only "schemas" attribute is used
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            [None],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            [None],
        ),
        (
            [
                # extensions are ignored
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
            [None],
        ),
    ),
)
def test_get_schema_for_resources(data, expected):
    schema = list_response.ListResponse([user.User, user.User])

    actual = schema.get_schemas_for_resources(data)

    assert isinstance(actual, type(expected))


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (
            [
                SCIMDataContainer(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                # extensions are ignored
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
            [user.User],
        ),
    ),
)
def test_get_schema_for_resources__returns_schema_for_bad_data_if_single_schema(data, expected):
    schema = list_response.ListResponse([user.User])

    actual = schema.get_schemas_for_resources(data)

    assert isinstance(actual, type(expected))
