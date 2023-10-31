import pytest

from src.parser.attributes.attributes import AttributeName


@pytest.mark.parametrize(
    (
        "input_",
        "expected_schema",
        "expected_full_attr",
        "expected_attr",
        "expected_sub_attr",
    ),
    (
        ("userName", "", "username", "username", ""),
        ("name.firstName", "", "name", "name", "firstname"),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "urn:ietf:params:scim:schemas:core:2.0:user",
            "urn:ietf:params:scim:schemas:core:2.0:user:username",
            "username",
            "",
        ),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName",
            "urn:ietf:params:scim:schemas:core:2.0:user",
            "urn:ietf:params:scim:schemas:core:2.0:user:name",
            "name",
            "firstname",
        ),
    ),
)
def test_attribute_identifier_is_parsed(
    input_, expected_schema, expected_full_attr, expected_attr, expected_sub_attr
):
    attr_name = AttributeName.parse(input_)

    assert attr_name.schema == expected_schema
    assert attr_name.full_attr == expected_full_attr
    assert attr_name.attr == expected_attr
    assert attr_name.sub_attr == expected_sub_attr


@pytest.mark.parametrize(
    "input_",
    (
        "attr_1.sub_attr_1.sub_attr_2",
        "",
        "attr with spaces",
        'emails[type eq "work"]',
        "(attr_with_parenthesis)",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName.blahblah",
    ),
)
def test_attribute_identifier_is_not_parsed_when_bad_input(input_):
    attr_name = AttributeName.parse(input_)

    assert attr_name is None


@pytest.mark.parametrize(
    ("attr_name", "expected"),
    (
        (AttributeName(attr="id"), "2819c223-7f76-453a-919d-413861904646"),
        (
            AttributeName(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
            "bjensen@example.com",
        ),
        (
            AttributeName(attr="userName"),
            "bjensen@example.com",
        ),
        (
            AttributeName(attr="meta", sub_attr="resourceType"),
            "User",
        ),
        (
            AttributeName(attr="name", sub_attr="givenName"),
            "Barbara",
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="familyName",
            ),
            "Jensen",
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="familyName",
            ),
            "Jensen",
        ),
        (
            AttributeName(
                attr="emails",
                sub_attr="type",
            ),
            None,  # no support for complex, multivalued attrs
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="employeeNumber",
            ),
            "701984",
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            "John Smith",
        ),
        (
            AttributeName(attr="employeeNumber"),
            "701984",
        ),
        (
            AttributeName(
                attr="manager",
                sub_attr="displayName",
            ),
            "John Smith",
        ),
    ),
)
def test_value_can_be_extracted(attr_name, expected, enterprise_user_data):
    actual = attr_name.extract(enterprise_user_data)

    assert actual == expected
