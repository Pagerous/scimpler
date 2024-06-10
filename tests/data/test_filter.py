import re

import pytest

from src.assets.schemas import User
from src.container import AttrRep, AttrRepFactory, BoundedAttrRep
from src.data.filter import Filter
from src.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
from src.registry import register_binary_operator, register_unary_operator


@pytest.mark.parametrize(
    "attr",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("operator", ("eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"))
def test_deserialize_basic_binary_attribute_filter(attr, operator):
    expected = {"op": operator, "attr": attr, "value": "bjensen"}
    filter_exp = f'{attr} {operator} "bjensen"'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [AttrRepFactory.deserialize(attr)]


@pytest.mark.parametrize(
    "full_attr",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("operator", ("eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"))
def test_deserialize_basic_binary_complex_attribute_filter(full_attr, operator):
    attr = AttrRepFactory.deserialize(full_attr)
    expected = {
        "op": operator,
        "attr": full_attr,
        "value": "bjensen",
    }
    filter_exp = f'{full_attr} {operator} "bjensen"'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [attr]


@pytest.mark.parametrize(
    "attr",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("operator", ("pr",))
def test_deserialize_basic_unary_attribute_filter(attr, operator):
    expected = {
        "op": operator,
        "attr": attr,
    }
    filter_exp = f"{attr} {operator}"

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [AttrRepFactory.deserialize(attr)]


@pytest.mark.parametrize(
    "full_attr",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("operator", ("pr",))
def test_deserialize_basic_unary_attribute_filter_with_complex_attribute(full_attr, operator):
    attr = AttrRepFactory.deserialize(full_attr)
    expected = {
        "op": operator,
        "attr": full_attr,
    }
    filter_exp = f"{full_attr} {operator}"

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [attr]


@pytest.mark.parametrize(
    "attr",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("sequence", ("  ", "\t\t", "\n", " \t", "\t ", "\n\n", " \n", "\n "))
def test_any_sequence_of_whitespaces_between_tokens_has_no_influence_on_filter(attr, sequence):
    expected = {"op": "eq", "attr": attr, "value": f"bjen{sequence}sen"}
    filter_exp = f'{attr}{sequence}{sequence}eq{sequence}"bjen{sequence}sen"'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [AttrRepFactory.deserialize(attr)]


@pytest.mark.parametrize(
    "full_attr",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("sequence", ("  ", "\t\t", "\n", " \t", "\t ", "\n\n", " \n", "\n "))
def test_any_sequence_of_whitespaces_between_tokens_has_no_influence_on_filter_with_complex_attr(
    full_attr, sequence
):
    attr = AttrRepFactory.deserialize(full_attr)
    expected = {
        "op": "eq",
        "attr": str(attr),
        "value": f"bjen{sequence}sen",
    }

    filter_exp = f'{full_attr}{sequence}{sequence}eq{sequence}"bjen{sequence}sen"'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [attr]


def test_basic_filters_can_be_combined_with_and_operator():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjensen"},
            {
                "op": "ne",
                "attr": "name.formatted",
                "value": "Crazy",
            },
            {
                "op": "co",
                "attr": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                "value": "bj",
            },
        ],
    }
    filter_exp = (
        'userName eq "bjensen" '
        'and name.formatted ne "Crazy" '
        'and urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


def test_basic_filters_can_be_combined_with_or_operator():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjensen"},
            {
                "op": "ne",
                "attr": "name.formatted",
                "value": "Crazy",
            },
            {
                "op": "co",
                "attr": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                "value": "bj",
            },
        ],
    }
    filter_exp = (
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'or urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep("userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="nickName",
        ),
    ]


def test_basic_filter_can_be_combined_with_not_operator():
    expected = {
        "op": "not",
        "sub_op": {
            "op": "eq",
            "attr": "userName",
            "value": "bjensen",
        },
    }
    filter_exp = 'not userName eq "bjensen"'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [AttrRep("userName")]


def test_precedence_of_logical_operators_is_preserved():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjensen"},
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "name.formatted",
                        "value": "Crazy",
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                            "value": "bj",
                        },
                    },
                ],
            },
        ],
    }
    filter_exp = (
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'and not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep("userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="nickName",
        ),
    ]


def test_whitespaces_between_tokens_with_logical_operators_has_no_influence_on_filter():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjen\tsen"},
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "name.formatted",
                        "value": "Craz\ny",
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                            "value": "b j",
                        },
                    },
                ],
            },
        ],
    }
    filter_exp = (
        'userName\t eq   "bjen\tsen" '
        'or\t  name.formatted    ne "Craz\ny" '
        'and \t\nnot  urn:ietf:params:scim:schemas:core:2.0:User:nickName co "b j"'
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep("userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="nickName",
        ),
    ]


def test_filter_groups_are_deserialized():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjensen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "name.formatted",
                        "value": "Crazy",
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr": "urn:ietf:params:scim:schemas:core:2.0:"
                                    "User:nickName",
                                    "value": "bj",
                                },
                            },
                            {"op": "eq", "attr": "id", "value": 1},
                        ],
                    },
                ],
            },
        ],
    }
    filter_exp = (
        'userName eq "bjensen" '
        "and "
        "("
        'name.formatted ne "Crazy" '
        'or (not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj" and id eq 1)'
        ")"
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep("userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="nickName",
        ),
        AttrRep("id"),
    ]


def test_any_sequence_of_whitespaces_has_no_influence_on_filter_with_groups():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjen  sen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "name.formatted",
                        "value": "Craz\ny",
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                                    "value": "b\t\tj",
                                },
                            },
                            {"op": "eq", "attr": "id", "value": 1},
                        ],
                    },
                ],
            },
        ],
    }
    filter_exp = (
        '\tuserName   eq \n"bjen  sen" '
        "and "
        "("
        '\t  name.formatted ne "Craz\ny" '
        "or ("
        '\tnot urn:ietf:params:scim:schemas:core:2.0:User:nickName   co "b\t\tj" and id eq 1'
        ")\n\n"
        ")"
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="nickName",
        ),
        AttrRep(attr="id"),
    ]


def test_basic_complex_attribute_filter_is_deserialized():
    expected = {
        "op": "complex",
        "attr": "emails",
        "sub_op": {
            "op": "eq",
            "attr": "type",
            "value": "work",
        },
    }
    filter_exp = 'emails[type eq "work"]'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [AttrRep(attr="emails", sub_attr="type")]


def test_complex_attribute_filter_with_logical_operators_is_deserialized():
    expected = {
        "op": "complex",
        "attr": "emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "eq",
                    "attr": "type",
                    "value": "work",
                },
                {
                    "op": "co",
                    "attr": "value",
                    "value": "@example.com",
                },
            ],
        },
    }
    filter_exp = 'emails[type eq "work" and value co "@example.com"]'

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep(attr="emails", sub_attr="type"),
        AttrRep(attr="emails", sub_attr="value"),
    ]


def test_complex_attribute_filter_with_logical_operators_and_groups_is_deserialized():
    expected = {
        "op": "complex",
        "attr": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr": "type",
                            "value": "work",
                        },
                        {
                            "op": "pr",
                            "attr": "primary",
                        },
                    ],
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr": "value",
                            "value": "@example.com",
                        },
                        {
                            "op": "co",
                            "attr": "display",
                            "value": "@example.com",
                        },
                    ],
                },
            ],
        },
    }
    filter_exp = (
        "urn:ietf:params:scim:schemas:core:2.0:User:emails["
        '(type eq "work" or primary pr) and '
        "("
        'value co "@example.com" or urn:ietf:params:scim:schemas:core:2.0:User:emails.display '
        'co "@example.com"'
        ")"
        "]"
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="emails",
            sub_attr=sub_attr,
        )
        for sub_attr in ["type", "primary", "value", "display"]
    ]


def test_any_sequence_of_whitespace_characters_has_no_influence_on_complex_attribute_filter():
    expected = {
        "op": "complex",
        "attr": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr": "type",
                            "value": "work",
                        },
                        {
                            "op": "pr",
                            "attr": "primary",
                        },
                    ],
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr": "value",
                            "value": "@ex am\nple.com",
                        },
                        {
                            "op": "co",
                            "attr": "display",
                            "value": "@example\t.com",
                        },
                    ],
                },
            ],
        },
    }
    filter_exp = (
        " \turn:ietf:params:scim:schemas:core:2.0:User:emails[  "
        "("
        'type \neq "work" or\t\t emails.primary pr'
        ") \tand\n "
        "(  "
        'value co "@ex am\nple.com" or '
        'urn:ietf:params:scim:schemas:core:2.0:User:emails.display co "@example\t.com"'
        ")"
        "]"
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="emails",
            sub_attr=sub_attr,
        )
        for sub_attr in ["type", "primary", "value", "display"]
    ]


def test_gargantuan_filter():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr": "userName", "value": "bjensen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "name.formatted",
                        "value": "Crazy",
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr": "urn:ietf:params:scim:schemas:core:2.0:"
                                    "User:nickName",
                                    "value": "bj",
                                },
                            },
                            {"op": "eq", "attr": "id", "value": 1},
                        ],
                    },
                ],
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "eq",
                                            "attr": "type",
                                            "value": "work",
                                        },
                                        {
                                            "op": "pr",
                                            "attr": "primary",
                                        },
                                    ],
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr": "value",
                                            "value": "@example.com",
                                        },
                                        {
                                            "op": "co",
                                            "attr": "display",
                                            "value": "@example.com",
                                        },
                                    ],
                                },
                            ],
                        },
                    },
                    {
                        "op": "complex",
                        "attr": "ims",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "eq",
                                            "attr": "type",
                                            "value": "work",
                                        },
                                        {
                                            "op": "pr",
                                            "attr": "primary",
                                        },
                                    ],
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr": "value",
                                            "value": "@example.com",
                                        },
                                        {
                                            "op": "co",
                                            "attr": "display",
                                            "value": "@example.com",
                                        },
                                    ],
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }
    filter_exp = (
        'userName eq "bjensen" and '
        "("
        'name.formatted ne "Crazy" or '
        '(not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj" and id eq 1)'
        ") and "
        "("
        "urn:ietf:params:scim:schemas:core:2.0:User:emails["
        '(type eq "work" or primary pr) and '
        "("
        'value co "@example.com" or urn:ietf:params:scim:schemas:core:2.0:User:emails.display '
        'co "@example.com"'
        ")"
        "] or "
        "ims["
        '(type eq "work" or primary pr) and '
        '(value co "@example.com" or display co "@example.com")'
        "]"
        ")"
    )

    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected
    assert filter_.attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name", sub_attr="formatted"),
        BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="nickName"),
        AttrRep(attr="id"),
    ] + [
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="emails",
            sub_attr=sub_attr,
        )
        for sub_attr in ["type", "primary", "value", "display"]
    ] + [
        AttrRep(attr="ims", sub_attr=sub_attr)
        for sub_attr in ["type", "primary", "value", "display"]
    ]
    assert Filter.deserialize(filter_.serialize()).to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "bjensen"',
            {
                "op": "eq",
                "attr": "userName",
                "value": "bjensen",
            },
        ),
        (
            'name.familyName co "O\'Malley"',
            {
                "op": "co",
                "attr": "name.familyName",
                "value": "O'Malley",
            },
        ),
        (
            'userName sw "J"',
            {
                "op": "sw",
                "attr": "userName",
                "value": "J",
            },
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:userName sw "J"',
            {
                "op": "sw",
                "attr": "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                "value": "J",
            },
        ),
        (
            "title pr",
            {
                "op": "pr",
                "attr": "title",
            },
        ),
        (
            'meta.lastModified gt "2011-05-13T04:42:34Z"',
            {
                "op": "gt",
                "attr": "meta.lastModified",
                "value": "2011-05-13T04:42:34Z",
            },
        ),
        (
            'meta.lastModified ge "2011-05-13T04:42:34Z"',
            {
                "op": "ge",
                "attr": "meta.lastModified",
                "value": "2011-05-13T04:42:34Z",
            },
        ),
        (
            'meta.lastModified lt "2011-05-13T04:42:34Z"',
            {
                "op": "lt",
                "attr": "meta.lastModified",
                "value": "2011-05-13T04:42:34Z",
            },
        ),
        (
            'meta.lastModified le "2011-05-13T04:42:34Z"',
            {
                "op": "le",
                "attr": "meta.lastModified",
                "value": "2011-05-13T04:42:34Z",
            },
        ),
        (
            'title pr and userType eq "Employee"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "pr",
                        "attr": "title",
                    },
                    {
                        "op": "eq",
                        "attr": "userType",
                        "value": "Employee",
                    },
                ],
            },
        ),
        (
            'title pr or userType eq "Intern"',
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "pr",
                        "attr": "title",
                    },
                    {
                        "op": "eq",
                        "attr": "userType",
                        "value": "Intern",
                    },
                ],
            },
        ),
        (
            'schemas eq "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"',
            {
                "op": "eq",
                "attr": "schemas",
                "value": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            },
        ),
        (
            'userType eq "Employee" and (emails co "example.com" or emails.value co "example.org")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr": "userType",
                        "value": "Employee",
                    },
                    {
                        "op": "or",
                        "sub_ops": [
                            {
                                "op": "co",
                                "attr": "emails",
                                "value": "example.com",
                            },
                            {
                                "op": "co",
                                "attr": "emails.value",
                                "value": "example.org",
                            },
                        ],
                    },
                ],
            },
        ),
        (
            'userType ne "Employee" '
            'and not (emails co "example.com" or emails.value co "example.org")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr": "userType",
                        "value": "Employee",
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "or",
                            "sub_ops": [
                                {
                                    "op": "co",
                                    "attr": "emails",
                                    "value": "example.com",
                                },
                                {
                                    "op": "co",
                                    "attr": "emails.value",
                                    "value": "example.org",
                                },
                            ],
                        },
                    },
                ],
            },
        ),
        (
            'userType eq "Employee" and (emails.type eq "work")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr": "userType",
                        "value": "Employee",
                    },
                    {
                        "op": "eq",
                        "attr": "emails.type",
                        "value": "work",
                    },
                ],
            },
        ),
        (
            'userType eq "Employee" and emails[type eq "work" and value co "@example.com"]',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr": "userType",
                        "value": "Employee",
                    },
                    {
                        "op": "complex",
                        "attr": "emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr": "type",
                                    "value": "work",
                                },
                                {
                                    "op": "co",
                                    "attr": "value",
                                    "value": "@example.com",
                                },
                            ],
                        },
                    },
                ],
            },
        ),
        (
            'emails[type eq "work" and value co "@example.com"] '
            'or ims[type eq "xmpp" and value co "@foo.com"]',
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr": "emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr": "type",
                                    "value": "work",
                                },
                                {
                                    "op": "co",
                                    "attr": "value",
                                    "value": "@example.com",
                                },
                            ],
                        },
                    },
                    {
                        "op": "complex",
                        "attr": "ims",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr": "type",
                                    "value": "xmpp",
                                },
                                {
                                    "op": "co",
                                    "attr": "value",
                                    "value": "@foo.com",
                                },
                            ],
                        },
                    },
                ],
            },
        ),
    ),
)
def test_rfc_7644_exemplary_filter(filter_exp, expected):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'userName eq "user123" and (id eq 1 or display co "user"',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user123" and (id eq 1 or display co "use)r"',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user123" and id eq 1 or display co "user")',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user(123" and id eq 1 or display co "user")',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user123") and (id eq 1 or display co "user"',
            {"_errors": [{"code": 100}, {"code": 100}]},
        ),
        (
            'userName eq "user(123") and (id eq 1 or display co "use)r"',
            {"_errors": [{"code": 100}, {"code": 100}]},
        ),
        (
            'userName eq "user123") and (id eq 1 or display co "user") '
            'or (id eq 2 or display co "user"',
            {"_errors": [{"code": 100}, {"code": 100}]},
        ),
        (
            'userName eq "user123") and ((id eq 1 or display co "user") '
            'or (id eq 2 or display co "user")',
            {"_errors": [{"code": 100}, {"code": 100}]},
        ),
        (
            'userName eq "user123" and (not (id eq 1 or display co "user")',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user123" and not (id eq 1 or display co "user"))',
            {"_errors": [{"code": 100}]},
        ),
        (
            'emails[type eq "work" and (display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 100}]},
        ),
        (
            'emails[type eq "work") and (display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 100}, {"code": 100}]},
        ),
        (
            'emails[type eq "work") and display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 100}]},
        ),
    ),
)
def test_number_of_group_brackets_must_match(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use(r123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "use(r123"},
                    {"op": "co", "attr": "display", "value": "us)er"},
                ],
            },
        ),
        (
            'userName eq "use(r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "use(r123"},
                    {"op": "co", "attr": "display", "value": "user"},
                ],
            },
        ),
        (
            'userName eq "user123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "user123"},
                    {"op": "co", "attr": "display", "value": "us)er"},
                ],
            },
        ),
    ),
)
def test_group_bracket_characters_are_ignored_when_inside_string_value(filter_exp, expected):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'emails[type eq "work" and display co "@example.com" or value co "@example"',
            {"_errors": [{"code": 101}]},
        ),
        (
            'emails type eq "work" and display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 101}]},
        ),
        ('emails[type eq "work" and ims[type eq "work"', {"_errors": [{"code": 107}]}),
        ('emails[type eq "work"] and ims[type eq "work"', {"_errors": [{"code": 101}]}),
        (
            'emails type eq "work"] and ims type eq "work"]',
            {"_errors": [{"code": 101}, {"code": 101}]},
        ),
    ),
)
def test_number_of_complex_attribute_brackets_must_match(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use[r123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "use[r123"},
                    {"op": "co", "attr": "display", "value": "us]er"},
                ],
            },
        ),
        (
            'userName eq "use[r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "use[r123"},
                    {"op": "co", "attr": "display", "value": "user"},
                ],
            },
        ),
        (
            'userName eq "user123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr": "userName", "value": "user123"},
                    {"op": "co", "attr": "display", "value": "us]er"},
                ],
            },
        ),
    ),
)
def test_complex_attribute_bracket_characters_are_ignored_when_inside_string_value(
    filter_exp, expected
):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'userName eq "user123" and',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'userName eq "user123" and',
                        },
                    }
                ]
            },
        ),
        (
            ' and userName eq "user123"',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and userName eq "user123"',
                        },
                    }
                ]
            },
        ),
        (
            'id eq 1 and and userName eq "user123"',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "id eq 1 and",
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and userName eq "user123"',
                        },
                    },
                ]
            },
        ),
        (
            'id eq 1 and userName eq "user123" and',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'userName eq "user123" and',
                        },
                    }
                ]
            },
        ),
        (
            'emails[type eq "work" and ]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'type eq "work" and',
                        },
                    }
                ]
            },
        ),
        (
            'emails[ and type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    }
                ]
            },
        ),
        (
            'emails[ and type eq "work" and]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'type eq "work" and',
                        },
                    },
                ]
            },
        ),
        (
            'and emails[ and type eq "work" and]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and emails[ and type eq "work" and]',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'type eq "work" and',
                        },
                    },
                ]
            },
        ),
        (
            'userName eq "user123" or',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'userName eq "user123" or',
                        },
                    },
                ]
            },
        ),
        (
            ' or userName eq "user123"',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or userName eq "user123"',
                        },
                    },
                ]
            },
        ),
        (
            'id eq 1 or or userName eq "user123"',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": "id eq 1 or",
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or userName eq "user123"',
                        },
                    },
                ]
            },
        ),
        (
            'id eq 1 or userName eq "user123" or',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'userName eq "user123" or',
                        },
                    },
                ]
            },
        ),
        (
            'emails[type eq "work" or ]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'type eq "work" or',
                        },
                    },
                ]
            },
        ),
        (
            'emails[ or type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work"',
                        },
                    },
                ]
            },
        ),
        (
            'emails[ or type eq "work" or]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work"',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'type eq "work" or',
                        },
                    },
                ]
            },
        ),
        (
            'or emails[ or type eq "work" or]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or emails[ or type eq "work" or]',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work"',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'type eq "work" or',
                        },
                    },
                ]
            },
        ),
        (
            'emails[ or type eq "work" and]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work" and',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'type eq "work" and',
                        },
                    },
                ]
            },
        ),
        (
            'or emails[ and type eq "work" or]',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'or emails[ and type eq "work" or]',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": 'and type eq "work" or',
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    },
                ]
            },
        ),
        (
            'userName eq "user123" or (id eq 1 and)',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "id eq 1 and",
                        },
                    },
                ]
            },
        ),
        (
            'userName eq "user123" or (and id eq 1)',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "and id eq 1",
                        },
                    },
                ]
            },
        ),
        (
            'userName eq "user123" or (and id eq 1 or )',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": "and id eq 1 or",
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "and id eq 1",
                        },
                    },
                ]
            },
        ),
        (
            'userName eq "user123" or (and id eq 1 or ) and ',
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "(and id eq 1 or ) and",
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "or",
                            "expression": "and id eq 1 or",
                        },
                    },
                    {
                        "code": 103,
                        "context": {
                            "operator": "and",
                            "expression": "and id eq 1",
                        },
                    },
                ]
            },
        ),
        (
            "not",
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "not",
                            "expression": "not",
                        },
                    },
                ]
            },
        ),
        (
            "userName eq",
            {
                "_errors": [
                    {
                        "code": 103,
                        "context": {
                            "operator": "eq",
                            "expression": "userName eq",
                        },
                    },
                ]
            },
        ),
    ),
)
def test_missing_operand_for_operator_causes_parsing_issues(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "apple banana",
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "operator": "banana",
                            "expression": "apple banana",
                        },
                    }
                ]
            },
        ),
        (
            'apple banana "pear"',
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "operator": "banana",
                            "expression": 'apple banana "pear"',
                        },
                    }
                ]
            },
        ),
        (
            '(a b "c") or (c d "e")',
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "operator": "b",
                            "expression": 'a b "c"',
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "d",
                            "expression": 'c d "e"',
                        },
                    },
                ]
            },
        ),
        (
            '(a b) and emails[c d "e" or g h]',
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "operator": "b",
                            "expression": "a b",
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "d",
                            "expression": 'c d "e"',
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "h",
                            "expression": "g h",
                        },
                    },
                ]
            },
        ),
    ),
)
def test_unknown_operator_causes_parsing_issues(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


def test_putting_complex_attribute_operator_inside_other_complex_attribute_operator_fails():
    expected_issues = {"_errors": [{"code": 107}]}
    filter_exp = 'emails[type eq work and phones[type eq "home"]]'
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'emai..ls[type eq "work"]',
            {"_errors": [{"code": 17, "context": {"attribute": "emai..ls"}}]},
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:emai..ls[type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:emai..ls",
                        },
                    }
                ]
            },
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:emails.bla.bla[type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": (
                                "urn:ietf:params:scim:schemas:core:2.0:User:emails.bla.bla"
                            ),
                        },
                    }
                ]
            },
        ),
        (
            'user..name eq "John Smith"',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "user..name",
                        },
                    }
                ]
            },
        ),
        (
            "user..name pr",
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "user..name",
                        },
                    }
                ]
            },
        ),
        (
            'user..name eq "John Smith" and very.first.name eq "John"',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "user..name",
                        },
                    },
                    {
                        "code": 17,
                        "context": {
                            "attribute": "very.first.name",
                        },
                    },
                ]
            },
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:user..name eq "John Smith"',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                        },
                    }
                ]
            },
        ),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:user..name pr",
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                        },
                    }
                ]
            },
        ),
        (
            (
                'urn:ietf:params:scim:schemas:core:2.0:User:user..name eq "John Smith" '
                'and urn:ietf:params:scim:schemas:core:2.0:User:very.first.name eq "John"'
            ),
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {
                            "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                        },
                    },
                    {
                        "code": 17,
                        "context": {
                            "attribute": (
                                "urn:ietf:params:scim:schemas:core:2.0:User:very.first.name"
                            ),
                        },
                    },
                ]
            },
        ),
    ),
)
def test_attribute_name_must_comform_abnf_rules(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "emails[]",
            {
                "_errors": [
                    {
                        "code": 108,
                        "context": {
                            "attribute": "emails",
                        },
                    }
                ]
            },
        ),
        (
            'emails[type eq "work"] and ims[]',
            {
                "_errors": [
                    {
                        "code": 108,
                        "context": {
                            "attribute": "ims",
                        },
                    }
                ]
            },
        ),
        (
            "emails[] and ims[]",
            {
                "_errors": [
                    {
                        "code": 108,
                        "context": {
                            "attribute": "emails",
                        },
                    },
                    {
                        "code": 108,
                        "context": {
                            "attribute": "ims",
                        },
                    },
                ]
            },
        ),
    ),
)
def test_lack_of_expression_inside_complex_attribute_is_discovered(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            '[type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {"attribute": ""},
                    }
                ]
            },
        ),
        (
            '[type eq "work"] and [type eq "home"]',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {"attribute": ""},
                    },
                    {
                        "code": 17,
                        "context": {"attribute": ""},
                    },
                ]
            },
        ),
        (
            'emails[type eq "work"] and [type eq "home"]',
            {
                "_errors": [
                    {
                        "code": 17,
                        "context": {"attribute": ""},
                    }
                ]
            },
        ),
    ),
)
def test_lack_of_top_level_complex_attribute_name_is_discovered(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[type eq "work" and ims[type eq "home"]]',
        'emails[type eq "work"] and ims[type eq "home" and phones[type eq "work"]]',
    ),
)
def test_presence_of_complex_attribute_inside_other_complex_attribute_is_discovered(
    filter_exp,
):
    expected_issues = {"_errors": [{"code": 107}]}
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        ("", {"_errors": [{"code": 105}]}),
        ("()", {"_errors": [{"code": 105}]}),
        ('userName eq "John" and ()', {"_errors": [{"code": 105}]}),
        ('() and userName eq "John"', {"_errors": [{"code": 105}]}),
        (
            '() or userName eq "John" and ()',
            {"_errors": [{"code": 105}, {"code": 105}]},
        ),
        ('emails[type eq "work" and ()]', {"_errors": [{"code": 105}]}),
        ('emails[() and type eq "work"]', {"_errors": [{"code": 105}]}),
        (
            'emails[() or type eq "work" and ()]',
            {"_errors": [{"code": 105}, {"code": 105}]},
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()]',
            {"_errors": [{"code": 105}, {"code": 105}]},
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()] and ()',
            {"_errors": [{"code": 105}, {"code": 105}, {"code": 105}]},
        ),
        (
            '() or userName eq "John" and emails[() or type eq "work" and ()] and ()',
            {"_errors": [{"code": 105}, {"code": 105}, {"code": 105}, {"code": 105}]},
        ),
    ),
)
def test_no_expression_is_discovered(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    "filter_exp",
    (
        'userName EQ "John"',
        'userName Eq "John"',
        'userName eQ "John"',
        "userName PR",
        "userName pR",
        "userName Pr",
    ),
)
def test_operators_are_case_insensitive(filter_exp):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    assert Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'attr eq "John"',
            {
                "op": "eq",
                "attr": "attr",
                "value": "John",
            },
        ),
        (
            "attr eq 1",
            {
                "op": "eq",
                "attr": "attr",
                "value": 1,
            },
        ),
        (
            "attr eq 1.0",
            {
                "op": "eq",
                "attr": "attr",
                "value": 1,
            },
        ),
        (
            "attr eq 1.2",
            {
                "op": "eq",
                "attr": "attr",
                "value": 1.2,
            },
        ),
        (
            "attr eq false",
            {
                "op": "eq",
                "attr": "attr",
                "value": False,
            },
        ),
        (
            "attr eq true",
            {
                "op": "eq",
                "attr": "attr",
                "value": True,
            },
        ),
        (
            "attr eq null",
            {
                "op": "eq",
                "attr": "attr",
                "value": None,
            },
        ),
    ),
)
def test_operators_are_case_insensitive(filter_exp, expected):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "userName eq blabla",
            {
                "_errors": [
                    {
                        "code": 109,
                        "context": {
                            "value": "blabla",
                        },
                    }
                ]
            },
        ),
        (
            "userName eq blabla and displayName eq not_true",
            {
                "_errors": [
                    {
                        "code": 109,
                        "context": {
                            "value": "blabla",
                        },
                    },
                    {
                        "code": 109,
                        "context": {
                            "value": "not_true",
                        },
                    },
                ]
            },
        ),
        (
            "emails[type eq blabla]",
            {
                "_errors": [
                    {
                        "code": 109,
                        "context": {
                            "value": "blabla",
                        },
                    }
                ]
            },
        ),
        (
            "emails[type eq blabla] or ims[type eq omnomnom]",
            {
                "_errors": [
                    {
                        "code": 109,
                        "context": {
                            "value": "blabla",
                        },
                    },
                    {
                        "code": 109,
                        "context": {
                            "value": "omnomnom",
                        },
                    },
                ]
            },
        ),
    ),
)
def test_bad_comparison_values_are_discovered(filter_exp, expected_issues):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "userName gt true",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": True,
                            "operator": "gt",
                        },
                    }
                ]
            },
        ),
        (
            "userName ge true",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": True,
                            "operator": "ge",
                        },
                    }
                ]
            },
        ),
        (
            "userName lt true",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": True,
                            "operator": "lt",
                        },
                    }
                ]
            },
        ),
        (
            "userName le true",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": True,
                            "operator": "le",
                        },
                    }
                ]
            },
        ),
        (
            "userName co null",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": None,
                            "operator": "co",
                        },
                    }
                ]
            },
        ),
        (
            "userName sw 1",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": 1,
                            "operator": "sw",
                        },
                    }
                ]
            },
        ),
        (
            "userName ew 2",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "value": 2,
                            "operator": "ew",
                        },
                    }
                ]
            },
        ),
    ),
)
def test_binary_operator_non_compatible_comparison_values_are_discovered(
    filter_exp, expected_issues
):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


def test_complex_sub_attribute_is_discovered():
    expected_issues = {"_errors": [{"code": 102}]}
    filter_exp = 'attr.sub_attr[type eq "work"]'
    issues = Filter.validate(filter_exp)
    assert issues.to_dict() == expected_issues

    with pytest.raises(ValueError, match="invalid filter expression"):
        Filter.deserialize(filter_exp)


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'attr eq "id eq 1 and value neq 2" and other_attr eq "id eq 1 or value neq 2"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr": "attr",
                        "value": "id eq 1 and value neq 2",
                    },
                    {
                        "op": "eq",
                        "attr": "other_attr",
                        "value": "id eq 1 or value neq 2",
                    },
                ],
            },
        ),
        (
            'emails[value eq "id eq 1 and attr neq 2"]',
            {
                "op": "complex",
                "attr": "emails",
                "sub_op": {
                    "op": "eq",
                    "attr": "value",
                    "value": "id eq 1 and attr neq 2",
                },
            },
        ),
        (
            'emails[value eq "ims[type eq "work"]"]',
            {
                "op": "complex",
                "attr": "emails",
                "sub_op": {
                    "op": "eq",
                    "attr": "value",
                    "value": 'ims[type eq "work"]',
                },
            },
        ),
    ),
)
def test_placing_filters_in_string_values_does_not_break_parsing(filter_exp, expected):
    issues = Filter.validate(filter_exp)
    assert issues.to_dict(msg=True) == {}

    filter_ = Filter.deserialize(filter_exp)
    assert filter_.to_dict() == expected


def test_binary_operator_can_be_registered():
    class Regex(BinaryAttributeOperator):
        SUPPORTED_SCIM_TYPES = {"string"}
        SUPPORTED_TYPES = {str}
        OPERATOR = staticmethod(lambda attr_value, op_value: re.fullmatch(op_value, attr_value))

        @classmethod
        def op(cls) -> str:
            return "re"

    register_binary_operator(Regex)

    filter_ = Filter.deserialize("userName re 'super\\d{4}user'")

    assert filter_({"userName": "super4132user"}, User)
    assert not filter_({"userName": "super413user"}, User)


def test_unary_operator_can_be_registered():
    class IsNice(UnaryAttributeOperator):
        SUPPORTED_SCIM_TYPES = {"string"}
        SUPPORTED_TYPES = {str}
        OPERATOR = staticmethod(lambda attr_value: attr_value == "Nice")

        @classmethod
        def op(cls) -> str:
            return "isNice"

    register_unary_operator(IsNice)

    filter_ = Filter.deserialize("userName isNice")

    assert filter_({"userName": "Nice"}, User)
    assert not filter_({"userName": "NotNice"}, User)


def test_attr_reps_do_not_contain_duplicates():
    filter_ = Filter.deserialize(
        "emails[type eq 'work' or Type eq 'home'] and (userName sw 'a' or username ew 'b')"
    )

    assert filter_.attr_reps == [
        AttrRep(attr="emails", sub_attr="type"),
        AttrRep(attr="userName"),
    ]


def test_attr_reps_are_not_returned_for_filters_with_bad_attributes():
    filter_ = Filter("whatever")  # noqa

    assert filter_.attr_reps == []


def test_filter_can_be_applied_on_multivalued_complex_attribute_if_no_sub_attr_specified():
    filter_ = Filter.deserialize("emails co 'example.com'")

    assert filter_({"emails": [{"value": "a@bad.com"}, {"value": "a@example.com"}]}, User)
    assert not filter_({"emails": [{"value": "a@bad.com"}]}, User)


def test_filter_can_be_applied_on_multivalued_complex_attribute_if_value_sub_attr_specified():
    filter_ = Filter.deserialize("emails.value co 'example.com'")

    assert filter_({"emails": [{"value": "a@bad.com"}, {"value": "a@example.com"}]}, User)
    assert not filter_({"emails": [{"value": "a@bad.com"}]}, User)


def test_filter_can_be_applied_on_multivalued_complex_attribute_if_other_sub_attr_specified():
    filter_ = Filter.deserialize("emails.display co 'example.com'")

    assert filter_({"emails": [{"display": "a@bad.com"}, {"display": "a@example.com"}]}, User)
    assert not filter_({"emails": [{"display": "a@bad.com"}]}, User)


def test_unknown_expression_error_is_returned_if_any_component_is_not_recognized():
    expected = {"_errors": [{"code": 106}]}

    actual = Filter.validate("a b c d")

    assert actual.to_dict() == expected


def test_type_error_is_raised_if_serializing_filter_with_unknown_operator():
    filter_ = Filter("whatever")  # noqa

    with pytest.raises(TypeError, match="unsupported filter type"):
        filter_.serialize()


def test_type_error_is_raised_if_converting_to_dict_filter_with_unknown_operator():
    filter_ = Filter("whatever")  # noqa

    with pytest.raises(TypeError, match="unsupported filter type"):
        filter_.to_dict()


def test_comparing_filter_to_anything_else_returns_false():
    assert Filter.deserialize("userName eq 'test'") != "userName eq 'test'"


def test_simple_filter_can_be_serialized():
    filter_ = Filter.deserialize("userName eq 'test'")

    serialized = filter_.serialize()

    assert serialized == "userName eq 'test'"


def test_filter_with_logical_operator_can_be_applied():
    filter_ = Filter.deserialize("userName ew 'ek' and emails co 'example.com'")

    assert filter_(
        {"userName": "Arek", "emails": [{"value": "a@bad.com"}, {"value": "a@example.com"}]}, User
    )
