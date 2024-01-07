import pytest

from src.parser.attributes import type as at
from src.parser.attributes.attributes import (
    Attribute,
    AttributeName,
    ComplexAttribute,
    extract,
    insert,
)


def test_parsing_is_skipped_if_value_not_provided():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    value, issues = attr.parse(
        value=None,
    )

    assert issues.to_dict() == {}
    assert value is None


def test_dumping_is_skipped_if_value_not_provided():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    value, issues = attr.dump(
        value=None,
    )

    assert issues.to_dict() == {}
    assert value is None


def test_multi_valued_attribute_parsing_fails_if_not_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.parse(
        value="non-list",
    )

    assert issues.to_dict() == {"_errors": [{"code": 6}]}
    assert value is None


def test_multi_valued_attribute_dumping_fails_if_not_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.dump(
        value="non-list",
    )

    assert issues.to_dict() == {"_errors": [{"code": 6}]}
    assert value is None


def test_multi_valued_attribute_parsing_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.parse(
        value=["a", "b", "c"],
    )

    assert not issues
    assert value == ["a", "b", "c"]


def test_multi_valued_attribute_dumping_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.dump(
        value=["a", "b", "c"],
    )

    assert not issues
    assert value == ["a", "b", "c"]


def test_multi_valued_attribute_values_are_parsed_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.parse(
        value=["a", 123],
    )

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}
    assert value == ["a", None]


def test_multi_valued_attribute_values_are_dumped_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.dump(
        value=["a", 123],
    )

    assert issues.to_dict() == {"1": {"_errors": [{"code": 31}]}}
    assert value == ["a", None]


def test_complex_attribute_sub_attributes_are_parsed_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.Integer, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        name="complex_attr",
    )
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
    }

    value, issues = attr.parse(value={"sub_attr_1": "123", "sub_attr_2": "123"})

    assert issues.to_dict() == expected_issues
    assert value == {"sub_attr_1": None, "sub_attr_2": None}


def test_complex_attribute_sub_attributes_are_dumped_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.Integer, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        name="complex_attr",
    )
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 31,
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 31,
                }
            ]
        },
    }

    value, issues = attr.dump(value={"sub_attr_1": "123", "sub_attr_2": "123"})

    assert issues.to_dict() == expected_issues
    assert value == {"sub_attr_1": None, "sub_attr_2": None}


def test_multivalued_complex_attribute_sub_attributes_are_parsed_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        multi_valued=True,
        name="complex_attr",
    )
    expected_issues = {
        "0": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
            "sub_attr_2": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
        "1": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
    }

    value, issues = attr.parse(
        value=[{"sub_attr_1": 123, "sub_attr_2": "123"}, {"sub_attr_1": 123, "sub_attr_2": 123}],
    )

    assert issues.to_dict() == expected_issues
    assert value == [
        {"sub_attr_1": None, "sub_attr_2": None},
        {"sub_attr_1": None, "sub_attr_2": 123},
    ]


def test_multivalued_complex_attribute_sub_attributes_are_dumped_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        multi_valued=True,
        name="complex_attr",
    )
    expected_issues = {
        "0": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 31,
                    }
                ]
            },
            "sub_attr_2": {
                "_errors": [
                    {
                        "code": 31,
                    }
                ]
            },
        },
        "1": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 31,
                    }
                ]
            },
        },
    }

    value, issues = attr.dump(
        value=[{"sub_attr_1": 123, "sub_attr_2": "123"}, {"sub_attr_1": 123, "sub_attr_2": 123}],
    )

    assert issues.to_dict() == expected_issues
    assert value == [
        {"sub_attr_1": None, "sub_attr_2": None},
        {"sub_attr_1": None, "sub_attr_2": 123},
    ]


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
    actual = extract(attr_name, enterprise_user_data)

    assert actual == expected


@pytest.mark.parametrize(
    ("attr_name", "value", "extension", "expected"),
    (
        (
            AttributeName(attr="id"),
            "2819c223-7f76-453a-919d-413861904646",
            False,
            {"id": "2819c223-7f76-453a-919d-413861904646"},
        ),
        (
            AttributeName(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
            "bjensen@example.com",
            False,
            {"username": "bjensen@example.com"},
        ),
        (
            AttributeName(attr="userName"),
            "bjensen@example.com",
            False,
            {"username": "bjensen@example.com"},
        ),
        (
            AttributeName(attr="meta", sub_attr="resourceType"),
            "User",
            False,
            {"meta": {"resourcetype": "User"}},
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="meta",
                sub_attr="resourceType",
            ),
            "User",
            False,
            {"meta": {"resourcetype": "User"}},
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="employeeNumber",
            ),
            "701984",
            True,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user": {
                    "employeenumber": "701984"
                }
            },
        ),
        (
            AttributeName(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            "John Smith",
            True,
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user": {
                    "manager": {"displayname": "John Smith"}
                }
            },
        ),
    ),
)
def test_value_can_be_inserted(attr_name, value, extension, expected):
    data = {}

    insert(data, attr_name, value, extension)

    assert data == expected
