import pytest

from src.container import AttrRep, BoundedAttrRep, Missing, SCIMDataContainer


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
            BoundedAttrRep(attr="meta", sub_attr="resourceType"),
            "User",
        ),
        (
            BoundedAttrRep(attr="name", sub_attr="givenName"),
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
            BoundedAttrRep(
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
    ("attr_rep", "value", "expand", "expected"),
    (
        (
            AttrRep(attr="id"),
            "2819c223-7f76-453a-919d-413861904646",
            False,
            {"id": "2819c223-7f76-453a-919d-413861904646"},
        ),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
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
            BoundedAttrRep(attr="meta", sub_attr="resourceType"),
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
                extension=True,
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
                extension=True,
            ),
            "John Smith",
            False,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "manager": {"displayName": "John Smith"}
                }
            },
        ),
    ),
)
def test_value_can_be_inserted_to_scim_data_container(attr_rep, value, expand, expected):
    container = SCIMDataContainer()

    container.set(attr_rep, value, expand)

    assert container.to_dict() == expected


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
