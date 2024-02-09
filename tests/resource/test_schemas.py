from copy import deepcopy

import pytest

from src.data.container import AttrRep, Missing, SCIMDataContainer
from src.data.operator import Equal
from src.data.path import PatchPath
from src.resource.schemas import list_response, patch_op, user
from src.resource.schemas.list_response import validate_items_per_page_consistency
from src.schemas import validate_resource_type_consistency, validate_schemas_field


def test_lack_of_data_is_validated():
    expected_issues = {"_errors": [{"code": 15}]}

    data, issues = user.User().parse(None)

    assert data is None
    assert issues.to_dict() == expected_issues


def test_bad_data_type_is_validated():
    expected_issues = {"_errors": [{"code": 2}]}

    data, issues = user.User().parse([])

    assert data == []
    assert issues.to_dict() == expected_issues


def test_user__correct_user_data_can_be_parsed(user_data_parse):
    expected_data = deepcopy(user_data_parse)
    user_data_parse["unexpected"] = 123  # should be filtered-out

    data, issues = user.User().parse(user_data_parse)

    assert issues.to_dict() == {}
    assert data.to_dict() == expected_data


def test_user__parsing_fails_if_bad_types(user_data_parse):
    user_data_parse["userName"] = 123  # noqa
    user_data_parse["name"]["givenName"] = 123  # noqa
    expected_data = deepcopy(user_data_parse)
    expected_data["userName"] = None
    expected_data["name"]["givenName"] = None
    expected_issues = {
        "userName": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "name": {
            "givenName": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            }
        },
    }

    data, issues = user.User().parse(user_data_parse)

    assert issues.to_dict() == expected_issues
    assert data.to_dict() == expected_data


def test_validate_schemas_field__unknown_additional_field_is_validated(user_data_parse):
    user_data_parse["schemas"].append("bad:user:schema")
    expected_issues = {"schemas": {"_errors": [{"code": 27}]}}
    schema = user.User()

    issues = validate_schemas_field(
        SCIMDataContainer(user_data_parse),
        schemas_=user_data_parse["schemas"],
        main_schema=schema.schema,
        known_schemas=schema.schemas,
    )

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_main_schema_is_missing(user_data_parse):
    user_data_parse["schemas"] = ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 28}]}}
    schema = user.User()

    issues = validate_schemas_field(
        SCIMDataContainer(user_data_parse),
        schemas_=user_data_parse["schemas"],
        main_schema=schema.schema,
        known_schemas=schema.schemas,
    )

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_extension_schema_is_missing(user_data_parse):
    user_data_parse["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 29}]}}
    schema = user.User()

    issues = validate_schemas_field(
        SCIMDataContainer(user_data_parse),
        schemas_=user_data_parse["schemas"],
        main_schema=schema.schema,
        known_schemas=schema.schemas,
    )

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__multiple_errors(user_data_parse):
    user_data_parse["schemas"] = ["bad:user:schema"]
    expected_issues = {"schemas": {"_errors": [{"code": 27}, {"code": 28}, {"code": 29}]}}
    schema = user.User()

    issues = validate_schemas_field(
        SCIMDataContainer(user_data_parse),
        schemas_=user_data_parse["schemas"],
        main_schema=schema.schema,
        known_schemas=schema.schemas,
    )

    assert issues.to_dict() == expected_issues


def test_validate_resource_type_consistency__fails_if_no_consistency():
    expected = {
        "meta": {
            "resourceType": {
                "_errors": [
                    {
                        "code": 17,
                    }
                ]
            }
        }
    }

    issues = validate_resource_type_consistency("Group", "User")

    assert issues.to_dict() == expected


def test_validate_resource_type_consistency__succeeds_if_consistency(user_data_dump):
    issues = validate_resource_type_consistency("User", "User")

    assert issues.to_dict() == {}


def test_validate_items_per_page_consistency__fails_if_not_matching_resources(list_user_data):
    expected = {
        "itemsPerPage": {"_errors": [{"code": 11}]},
        "Resources": {"_errors": [{"code": 11}]},
    }

    issues = validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=1,
    )

    assert issues.to_dict() == expected


def test_validate_items_per_page_consistency__succeeds_if_correct_data(list_user_data):
    issues = validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=2,
    )

    assert issues.to_dict() == {}


def test_list_response__dumping_resources_fails_if_bad_type(list_user_data, list_user_data_dumped):
    schema = list_response.ListResponse(resource_schemas=[user.User()])
    list_user_data["Resources"][0]["userName"] = 123
    list_user_data["Resources"][1]["userName"] = 123
    list_user_data_dumped["Resources"][0]["userName"] = None
    list_user_data_dumped["Resources"][1]["userName"] = None
    expected_issues = {
        "Resources": {
            "0": {"userName": {"_errors": [{"code": 2}]}},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        }
    }

    data, issues = schema.dump(list_user_data)

    assert issues.to_dict() == expected_issues
    assert data.to_dict() == list_user_data_dumped


def test_list_response__dumping_resources_succeeds_for_correct_data(
    list_user_data, list_user_data_dumped
):
    schema = list_response.ListResponse(resource_schemas=[user.User()])
    # below fields should be filtered-out
    list_user_data["unexpected"] = 123
    list_user_data["Resources"][0]["unexpected"] = 123
    list_user_data["Resources"][1]["name"]["unexpected"] = 123

    data, issues = schema.dump(list_user_data)

    assert issues.to_dict() == {}
    assert data.to_dict() == list_user_data_dumped


def test_dump_resources__resources_with_bad_type_are_reported(
    list_user_data, list_user_data_dumped
):
    schema = list_response.ListResponse(resource_schemas=[user.User()])
    list_user_data["Resources"][0] = []
    list_user_data["Resources"][1]["userName"] = 123
    list_user_data_dumped["Resources"][0] = None
    list_user_data_dumped["Resources"][1]["userName"] = None
    expected = {
        "Resources": {
            "0": {"_errors": [{"code": 2}]},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        }
    }

    data, issues = schema.dump(list_user_data)

    assert issues.to_dict() == expected
    assert data.to_dict() == list_user_data_dumped


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
            [user.User()],
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
def test_list_response__get_schema_for_resources(data, expected):
    schema = list_response.ListResponse(resource_schemas=[user.User(), user.User()])

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
            [user.User()],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            [user.User()],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User()],
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
            [user.User()],
        ),
    ),
)
def test_list_response__get_schema_for_resources__returns_schema_for_bad_data_if_single_schema(
    data, expected
):
    schema = list_response.ListResponse(resource_schemas=[user.User()])

    actual = schema.get_schemas_for_resources(data)

    assert isinstance(actual, type(expected))


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        (
            PatchPath(
                attr_rep=AttrRep(attr="nonexisting"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="non", sub_attr="existing"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=Equal(
                    attr_rep=AttrRep(attr="emails", sub_attr="nonexisting"), value="whatever"
                ),
                complex_filter_attr_rep=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=Equal(
                    attr_rep=AttrRep(attr="emails", sub_attr="type"), value="whatever"
                ),
                complex_filter_attr_rep=AttrRep(attr="emails", sub_attr="nonexisting"),
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=Equal(
                    attr_rep=AttrRep(attr="emails", sub_attr="type"), value="work"
                ),
                complex_filter_attr_rep=AttrRep(attr="emails", sub_attr="value"),
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=Equal(
                    attr_rep=AttrRep(attr="emails", sub_attr="type"), value="work"
                ),
                complex_filter_attr_rep=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="name", sub_attr="familyName"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            {},
        ),
    ),
)
def test_validate_operation_path(path, expected_issues):
    issues = patch_op.validate_operation_path(schema=user.User(), path=path)

    assert issues.to_dict() == expected_issues


def test_patch_op__add_operation_without_path_can_be_parsed():
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "value": {
                    "ignore^me": 42,
                    "name": {
                        "formatted": "Ms. Barbara J Jensen III",
                        "ignore^me": 42,
                    },
                    "userName": "bjensen",
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "ignore^me": 42,
                        "department": "Tour Operations",
                        "manager": {
                            "value": "Jan Kowalski",
                        },
                    },
                },
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": Missing,
                "value": {
                    "name": {
                        "formatted": "Ms. Barbara J Jensen III",
                    },
                    "userName": "bjensen",
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "department": "Tour Operations",
                        "manager": {
                            "value": "Jan Kowalski",
                        },
                    },
                },
            }
        ],
    }

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == {}
    assert actual_data.to_dict() == expected_data


def test_parse_add_operation_without_path__fails_for_incorrect_data():
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "value": {
                    "name": {
                        "formatted": 123,
                    },
                    "userName": 123,
                    "emails": [{"value": "bjensen@example.com", "type": 123}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "department": 123,
                        "manager": {
                            "displayName": 123,
                        },
                    },
                },
            },
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [None],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "name": {"formatted": {"_errors": [{"code": 2}]}},
                    "userName": {"_errors": [{"code": 2}]},
                    "emails": {"0": {"type": {"_errors": [{"code": 2}]}}},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "department": {"_errors": [{"code": 2}]},
                        "manager": {"displayName": {"_errors": [{"code": 2}, {"code": 304}]}},
                    },
                }
            }
        }
    }

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == expected_issues
    assert actual_data.to_dict() == expected_data


def test_parse_add_operation_without_path__fails_if_attribute_is_readonly():
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "value": {"meta": {"resourceType": "Users"}},
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [None],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "meta": {
                        "_errors": [{"code": 304}],
                        "resourceType": {"_errors": [{"code": 304}]},
                    },
                }
            }
        }
    }

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == expected_issues
    assert actual_data.to_dict() == expected_data


@pytest.mark.parametrize(
    ("path", "value", "expected_value_issues"),
    (
        (
            "userName",
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            "name.formatted",
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            "name",
            {"formatted": 123, "familyName": 123},
            {"formatted": {"_errors": [{"code": 2}]}, "familyName": {"_errors": [{"code": 2}]}},
        ),
        (
            "name",
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            "emails",
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            "emails",
            [{"type": 123, "value": 123}],
            {"0": {"type": {"_errors": [{"code": 2}]}, "value": {"_errors": [{"code": 2}]}}},
        ),
        (
            "emails",
            {"type": "home", "value": "home@example.com"},
            {"_errors": [{"code": 2}]},
        ),
        (
            'emails[type eq "work"].value',
            123,
            {"_errors": [{"code": 2}]},
        ),
    ),
)
def test_parse_add_operation__fails_for_incorrect_data(path, value, expected_value_issues):
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": path,
                "value": value,
            }
        ],
    }
    expected_issues = {"Operations": {"0": {"value": expected_value_issues}}}
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [None],
    }

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == expected_issues
    assert actual_data.to_dict() == expected_data


@pytest.mark.parametrize(
    ("path", "expected_path", "value", "expected_value"),
    (
        (
            "userName",
            PatchPath(
                attr_rep=AttrRep(attr="userName"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            "bjensen",
            "bjensen",
        ),
        (
            "name.formatted",
            PatchPath(
                attr_rep=AttrRep(attr="name", sub_attr="formatted"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            "Jan Kowalski",
            "Jan Kowalski",
        ),
        (
            "name",
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            {"formatted": "Jan Kowalski", "familyName": "Kowalski"},
            SCIMDataContainer({"formatted": "Jan Kowalski", "familyName": "Kowalski"}),
        ),
        (
            "emails",
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=None,
                complex_filter_attr_rep=None,
            ),
            [{"type": "work", "value": "work@example.com"}],
            [SCIMDataContainer({"type": "work", "value": "work@example.com"})],
        ),
        (
            'emails[type eq "work"].value',
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                complex_filter=Equal(
                    attr_rep=AttrRep(attr="emails", sub_attr="type"),
                    value="work",
                ),
                complex_filter_attr_rep=AttrRep(attr="emails", sub_attr="value"),
            ),
            "work@example.com",
            "work@example.com",
        ),
    ),
)
def test_parse_add_operation__succeeds_on_correct_data(path, expected_path, value, expected_value):
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": path,
                "value": value,
            }
        ],
    }

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == {}
    assert actual_data["Operations"][0]["value"] == expected_value
    assert actual_data["Operations"][0]["path"].attr_rep == expected_path.attr_rep
    if expected_path.complex_filter:
        assert (
            actual_data["Operations"][0]["path"].complex_filter.value
            == expected_path.complex_filter.value
        )
        assert (
            actual_data["Operations"][0]["path"].complex_filter.attr_rep
            == expected_path.complex_filter.attr_rep
        )
    if expected_path.complex_filter_attr_rep:
        assert (
            actual_data["Operations"][0]["path"].complex_filter_attr_rep
            == expected_path.complex_filter_attr_rep
        )


@pytest.mark.parametrize(
    ("path", "value"),
    (
        ("id", "123"),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
            "The Grok",
        ),
        ("meta", {"resourceType": "Users"}),
        ("groups", [{"type": "direct", "value": "admins"}]),
        ('groups[type eq "direct"].value', "admins"),
    ),
)
def test_parse_add_operation__fails_if_attribute_is_readonly(path, value):
    schema = patch_op.PatchOp(resource_schema=user.User())
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": path,
                "value": value,
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [None],
    }
    expected_issues = {"Operations": {"0": {"value": {"_errors": [{"code": 304}]}}}}

    actual_data, issues = schema.parse(input_data)

    assert issues.to_dict() == expected_issues
    assert actual_data.to_dict() == expected_data
