import pytest

from src.data import type as at
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import AttrRep, SCIMDataContainer


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


def test_multi_valued_attribute_parsing_fails_if_not_provided_list():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.parse(
        value="non-list",
    )

    assert issues.to_dict() == {"_errors": [{"code": 2}]}
    assert value is None


def test_multi_valued_attribute_dumping_fails_if_not_provided_list():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    value, issues = attr.dump(
        value="non-list",
    )

    assert issues.to_dict() == {"_errors": [{"code": 2}]}
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

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}
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

    value, issues = attr.parse(value=SCIMDataContainer({"sub_attr_1": "123", "sub_attr_2": "123"}))

    assert issues.to_dict() == expected_issues
    assert value.to_dict() == {"sub_attr_1": None, "sub_attr_2": None}


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

    value, issues = attr.dump(value=SCIMDataContainer({"sub_attr_1": "123", "sub_attr_2": "123"}))

    assert issues.to_dict() == expected_issues
    assert value.to_dict() == {"sub_attr_1": None, "sub_attr_2": None}


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
        value=[
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": "123"}),
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": 123}),
        ],
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

    value, issues = attr.dump(
        value=[
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": "123"}),
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": 123}),
        ],
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
        ("userName", "", "userName", "userName", ""),
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
    ),
)
def test_attribute_identifier_is_parsed(
    input_, expected_schema, expected_full_attr, expected_attr, expected_sub_attr
):
    attr_rep = AttrRep.parse(input_)

    assert attr_rep.schema == expected_schema
    assert attr_rep.attr_with_schema == expected_full_attr
    assert attr_rep.attr == expected_attr
    assert attr_rep.sub_attr == expected_sub_attr


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
    attr_rep = AttrRep.parse(input_)

    assert attr_rep is None
