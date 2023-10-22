import pytest

from src.parser.attributes.attributes import AttributeName


@pytest.mark.parametrize(
    ("input_", "expected_schema", "expected_full_attr", "expected_attr", "expected_sub_attr"),
    (
        ("userName", "", "userName",  "userName", ""),
        ("name.firstName", "", "name", "name", "firstName"),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "userName",
            "",
        ),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName",
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:core:2.0:User:name",
            "name",
            "firstName",
        ),
    )
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
        "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName.blahblah"
    )
)
def test_attribute_identifier_is_not_parsed_when_bad_input(input_):
    attr_name = AttributeName.parse(input_)

    assert attr_name is None
