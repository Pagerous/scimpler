import pytest

from src.container import (
    AttrRep,
    BoundedAttrRep,
    Invalid,
    Missing,
    SchemaURI,
    SCIMDataContainer,
)


@pytest.mark.parametrize(
    ("attr_rep", "expected"),
    (
        (AttrRep(attr="id"), "2819c223-7f76-453a-919d-413861904646"),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
            "bjensen@example.com",
        ),
        (
            AttrRep(attr="userName"),
            "bjensen@example.com",
        ),
        (
            AttrRep(attr="meta", sub_attr="resourceType"),
            "User",
        ),
        (
            AttrRep(attr="name", sub_attr="givenName"),
            "Barbara",
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="familyName",
            ),
            "Jensen",
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="familyName",
            ),
            "Jensen",
        ),
        (
            AttrRep(
                attr="emails",
                sub_attr="type",
            ),
            ["work", "home"],
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="employeeNumber",
            ),
            "1",
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            "John Smith",
        ),
    ),
)
def test_value_from_scim_data_container_can_be_retrieved(attr_rep, expected, user_data_server):
    actual = SCIMDataContainer(user_data_server).get(attr_rep)

    assert actual == expected


@pytest.mark.parametrize(
    ("key", "value", "expand", "expected"),
    (
        (
            AttrRep(attr="id"),
            "2819c223-7f76-453a-919d-413861904646",
            False,
            {"id": "2819c223-7f76-453a-919d-413861904646"},
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="userName",
            ),
            "bjensen@example.com",
            False,
            {"userName": "bjensen@example.com"},
        ),
        (
            AttrRep(attr="userName"),
            "bjensen@example.com",
            False,
            {"userName": "bjensen@example.com"},
        ),
        (
            AttrRep(attr="meta", sub_attr="resourceType"),
            "User",
            False,
            {"meta": {"resourceType": "User"}},
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="meta",
                sub_attr="resourceType",
            ),
            "User",
            False,
            {"meta": {"resourceType": "User"}},
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="emails",
                sub_attr="type",
            ),
            ["work", "home"],
            True,
            {"emails": [{"type": "work"}, {"type": "home"}]},
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="emails",
                sub_attr="type",
            ),
            [Missing, "home"],
            True,
            {"emails": [{}, {"type": "home"}]},
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="employeeNumber",
            ),
            "701984",
            False,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "701984"
                }
            },
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            "John Smith",
            False,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "manager": {"displayName": "John Smith"}
                }
            },
        ),
        (
            SchemaURI("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"),
            {"employeeNumber": "10", "manager": {"displayName": "John Smith"}},
            False,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "10",
                    "manager": {"displayName": "John Smith"},
                }
            },
        ),
    ),
)
def test_value_can_be_inserted_to_scim_data_container(key, value, expand, expected):
    container = SCIMDataContainer()

    container.set(key, value, expand)

    assert container == expected


def test_attr_value_in_container_can_be_reassigned():
    container = SCIMDataContainer()
    container.set("key", 123)

    container.set("KEY", 456)

    assert container.get("key") == 456


def test_sub_attr_value_in_container_can_be_reassigned():
    container = SCIMDataContainer()
    container.set("key.subkey", 123)

    container.set("KEY.SUBKEY", 456)

    assert container.get("key.subkey") == 456


def test_can_set_and_retrieve_sub_attrs_for_multivalued_complex_attr():
    container = SCIMDataContainer()

    container.set("KEY.SUBKEY", [4, 5, 6], expand=True)

    assert container.get("key.subkey") == [4, 5, 6]
    assert container.to_dict() == {"KEY": [{"SUBKEY": 4}, {"SUBKEY": 5}, {"SUBKEY": 6}]}


def test_sub_attr_bigger_list_value_in_container_can_be_reassigned():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2], expand=True)

    container.set("KEY.SUBKEY", [4, 5, 6], expand=True)

    assert container.get("key.subkey") == [4, 5, 6]
    assert container.to_dict() == {"key": [{"SUBKEY": 4}, {"SUBKEY": 5}, {"SUBKEY": 6}]}


def test_can_not_reassign_simple_value_to_sub_attr_when_expanding():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2], expand=True)

    with pytest.raises(KeyError, match=r"can not assign"):
        container.set("KEY.SUBKEY", 1, expand=True)


def test_sub_attr_smaller_list_value_in_container_can_be_reassigned():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2, 3], expand=True)

    container.set("KEY.SUBKEY", [4, 5], expand=True)

    assert container.get("key.subkey") == [4, 5, 3]


def test_assigning_sub_attr_to_non_complex_attr_fails():
    container = SCIMDataContainer()
    container.set("key", 1)

    with pytest.raises(KeyError, match=r"can not assign \(subkey, \[1, 2, 3\]\) to 'key'"):
        container.set("key.subkey", [1, 2, 3])


def test_multivalued_sub_attr_can_be_set_and_retrieved():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2, 3])

    assert container.get("key.subkey") == [1, 2, 3]
    assert container.to_dict() == {"key": {"subkey": [1, 2, 3]}}


def test_multivalued_sub_attr_can_be_set_and_reassigned():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2, 3])
    container.set("KEY.SUBKEY", [4, 5, 6])

    assert container.get("key.subkey") == [4, 5, 6]
    assert container.to_dict() == {"key": {"SUBKEY": [4, 5, 6]}}


def test_reassigning_simple_multivalued_with_expanded_value_fails():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2, 3])

    with pytest.raises(KeyError, match="can not assign"):
        container.set("KEY.SUBKEY", [4, 5, 6], expand=True)


def test_extension_can_be_reassigned():
    container = SCIMDataContainer()
    container.set(SchemaURI("my:schema:extension"), {"a": "b"})

    container.set(SchemaURI("MY:schema:EXTENSION"), {"a": "C"})

    assert container.get(SchemaURI("my:SCHEMA:extension")) == {"a": "C"}


def test_can_reassign_primitive_value_to_simple_multivalued_attr():
    container = SCIMDataContainer()
    container.set("key.subkey", [1, 2, 3])
    container.set("KEY.SUBKEY", 4)

    assert container.get("key.SUBKEY") == 4
    assert container.to_dict() == {"key": {"SUBKEY": 4}}


def test_can_set_and_retrieve_simple_multivalued_attr():
    container = SCIMDataContainer()

    container.set("key", [1, 2, 3])

    assert container.get("KEY") == [1, 2, 3]
    assert container.to_dict() == {"key": [1, 2, 3]}


def test_reassign_simple_multivalued_attr():
    container = SCIMDataContainer()

    container.set("key", [1, 2, 3])
    container.set("KEY", [4, 5, 6])

    assert container.get("KEY") == [4, 5, 6]
    assert container.to_dict() == {"KEY": [4, 5, 6]}


def test_creating_container_removes_duplicates():
    container = SCIMDataContainer({"a": 1, "A": 2})

    assert container.to_dict() == {"A": 2}


def test_bounded_attr_creation_fails_if_bad_attr_name():
    with pytest.raises(ValueError, match="is not valid attr name"):
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="bad^attr",
        )


def test_bounded_attr_creation_fails_if_bad_sub_attr_name():
    with pytest.raises(ValueError, match="'.*' is not valid attr name"):
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="attr",
            sub_attr="bad^sub^attr",
        )


@pytest.mark.parametrize(
    ("attr_1", "attr_2", "expected"),
    (
        (AttrRep(attr="attr"), AttrRep(attr="ATTR"), True),
        (AttrRep(attr="abc"), AttrRep(attr="cba"), False),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
            AttrRep(attr="UserName"),
            True,
        ),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="name"),
            BoundedAttrRep(schema="urn:ietf:params:SCIM:schemas:core:2.0:user", attr="NAME"),
            True,
        ),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="nonExisting"),
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="nonExisting",
            ),
            False,
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="formatted",
            ),
            BoundedAttrRep(
                schema="urn:ietf:params:SCIM:schemas:core:2.0:User",
                attr="NAME",
                sub_attr="FORMATTED",
            ),
            True,
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="givenName",
            ),
            BoundedAttrRep(
                schema="urn:ietf:params:SCIM:schemas:core:2.0:User",
                attr="NAME",
                sub_attr="FORMATTED",
            ),
            False,
        ),
        (AttrRep(attr="attr"), "attr", False),
    ),
)
def test_attr_rep_can_be_compared(attr_1, attr_2, expected):
    assert (attr_1 == attr_2) is expected


def test_invalid_type_repr():
    assert repr(Invalid) == "Invalid"


def test_missing_type_repr():
    assert repr(Missing) == "Missing"


def test_non_string_keys_are_excluded_from_container():
    data = {"a": "b", 1: 2, True: False}
    container = SCIMDataContainer(data)

    assert container.to_dict() == {"a": "b"}


def test_container_repr():
    container = SCIMDataContainer({"a": "b", "c": "d", "e": "f"})

    assert repr(container) == "SCIMDataContainer({'a': 'b', 'c': 'd', 'e': 'f'})"


@pytest.mark.parametrize(
    ("data", "attr_rep", "expected", "remaining"),
    (
        (
            {"a": 1, "b": 2, "c": 3},
            AttrRep(attr="a"),
            1,
            Missing,
        ),
        (
            {
                "a": 1,
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"b": 2},
                "c": 3,
            },
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User", attr="b"
            ),
            2,
            Missing,
        ),
        (
            {
                "a": 1,
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"b": {"d": 4}},
                "c": 3,
            },
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="b",
                sub_attr="d",
            ),
            4,
            Missing,
        ),
        (
            {
                "a": 1,
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"b": {"d": 4}},
                "c": 3,
            },
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User", attr="b"
            ),
            {"d": 4},
            Missing,
        ),
        (
            {"a": 1, "b": [{"d": 4, "e": 5}, {"d": 6, "e": 7}], "c": 3},
            AttrRep(attr="b", sub_attr="d"),
            [4, 6],
            [Missing, Missing],
        ),
        (
            {"a": 1, "b": [1, 2, 3], "c": 3},
            AttrRep(attr="b", sub_attr="d"),
            [Missing, Missing, Missing],
            [Missing, Missing, Missing],
        ),
        (
            {"a": 1},
            AttrRep(attr="a", sub_attr="b"),
            Missing,
            Missing,
        ),
        (
            {
                "a": 1,
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"b": {"d": 4}},
                "c": 3,
            },
            SchemaURI("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"),
            {"b": {"d": 4}},
            Missing,
        ),
        (
            {
                "a": 1,
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"b": {"d": 4}},
                "c": 3,
            },
            SchemaURI("non:existing:extension"),
            Missing,
            Missing,
        ),
        (
            {"a": 1, "c": 3},
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User", attr="manager"
            ),
            Missing,
            Missing,
        ),
    ),
)
def test_entry_can_be_popped_from_container(data, attr_rep, expected, remaining):
    container = SCIMDataContainer(data)

    actual = container.pop(attr_rep)

    assert actual == expected
    assert container.get(attr_rep) == remaining


def test_schema_uri_creation_fails_if_bad_uri():
    with pytest.raises(ValueError, match="not a valid schema URI"):
        SchemaURI("bad^uri")


@pytest.mark.parametrize(
    ("container_1", "container_2", "expected"),
    (
        (
            SCIMDataContainer(),
            SCIMDataContainer(),
            True,
        ),
        (
            SCIMDataContainer(
                {
                    "userName": "bjensen",
                    "name": {"formatted": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "employeeNumber": "10",
                        "manager": {"displayName": "Kowalski"},
                    },
                }
            ),
            SCIMDataContainer(
                {
                    "USERNAME": "bjensen",
                    "NAME": {"FORMATTED": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "EMPLOYEENUMBER": "10",
                        "MANAGER": {"DISPLAYNAME": "Kowalski"},
                    },
                }
            ),
            True,
        ),
        (
            SCIMDataContainer(
                {
                    "userName": "bjensen",
                    "name": {"formatted": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "employeeNumber": "10",
                        "manager": {"displayName": "Kowalski"},
                    },
                }
            ),
            SCIMDataContainer(
                {
                    "NAME": {"FORMATTED": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "EMPLOYEENUMBER": "10",
                        "MANAGER": {"DISPLAYNAME": "Kowalski"},
                    },
                }
            ),
            False,
        ),
        (
            SCIMDataContainer(
                {
                    "name": {"formatted": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "employeeNumber": "10",
                        "manager": {"displayName": "Kowalski"},
                    },
                }
            ),
            SCIMDataContainer(
                {
                    "USERNAME": "bjensen",
                    "NAME": {"FORMATTED": "Bjensen"},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "EMPLOYEENUMBER": "10",
                        "MANAGER": {"DISPLAYNAME": "Kowalski"},
                    },
                }
            ),
            False,
        ),
    ),
)
def test_containers_can_be_compared(container_1, container_2, expected):
    assert (container_1 == container_2) is expected
