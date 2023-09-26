import pytest

from src.parser.filter.filter import parse_filter
from src.parser.filter.utils import to_dict


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    )
)
@pytest.mark.parametrize(
    "operator",
    ("eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le")
)
def test_parse_basic_binary_attribute_filter(attr_name, operator):
    expected = {
        "op": operator,
        "attr_name": attr_name,
        "value": '"bjensen"'
    }
    filter_exp = f'{attr_name} {operator} "bjensen"'

    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    )
)
@pytest.mark.parametrize(
    "operator",
    ("pr", )
)
def test_parse_basic_unary_attribute_filter(attr_name, operator):
    expected = {
        "op": operator,
        "attr_name": attr_name,
    }
    filter_exp = f'{attr_name} {operator}'

    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    )
)
@pytest.mark.parametrize(
    "sequence",
    ("  ", "\t\t", "\n", " \t", "\t ", "\n\n", " \n", "\n ")
)
def test_any_sequence_of_whitespaces_between_tokens_has_no_influence_on_filter(attr_name, sequence):
    expected = {
        "op": "eq",
        "attr_name": attr_name,
        "value": f'"bjen{sequence}sen"'
    }
    filter_exp = f'{attr_name}{sequence}{sequence}eq{sequence}"bjen{sequence}sen"'

    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


def test_basic_filters_can_be_combined_with_and_operator():
    expected = {
        "op": "and",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"'
            },
            {
                "op": "ne",
                "attr_name": "name.formatted",
                "value": '"Crazy"'
            },
            {
                "op": "co",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                "value": '"bj"'
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName eq "bjensen" '
        'and name.formatted ne "Crazy" '
        'and urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_basic_filters_can_be_combined_with_or_operator():
    expected = {
        "op": "or",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"'
            },
            {
                "op": "ne",
                "attr_name": "name.formatted",
                "value": '"Crazy"'
            },
            {
                "op": "co",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                "value": '"bj"'
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'or urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"')

    assert errors == []
    assert to_dict(filter_) == expected


def test_precedence_of_logical_operators_is_preserved():
    expected = {
        "op": "or",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"'
            },
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "name.formatted",
                        "value": '"Crazy"',
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                            "value": '"bj"'
                        }
                    }
                ]
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'and not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_any_sequence_of_whitespaces_between_tokens_with_logical_operators_has_no_influence_on_filter():
    expected = {
        "op": "or",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjen\tsen"'
            },
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "name.formatted",
                        "value": '"Craz\ny"',
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                            "value": '"b j"'
                        }
                    }
                ]
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName\t eq   "bjen\tsen" '
        'or\t  name.formatted    ne "Craz\ny" '
        'and \t\nnot  urn:ietf:params:scim:schemas:core:2.0:User:nickName co "b j"'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_filter_groups_are_parsed():
    expected = {
        "op": "and",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"'
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "name.formatted",
                        "value": '"Crazy"',
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                                    "value": '"bj"'
                                },
                             },
                            {
                                "op": "eq",
                                "attr_name": "id",
                                "value": "1"
                            },
                        ]
                    }
                ]
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName eq "bjensen" '
        'and '
        '('
        'name.formatted ne "Crazy" '
        'or (not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj" and id eq 1)'
        ')'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_any_sequence_of_whitespaces_has_no_influence_on_filter_with_groups():
    expected = {
        "op": "and",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjen  sen"'
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "name.formatted",
                        "value": '"Craz\ny"',
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                                    "value": '"b\t\tj"'
                                },
                             },
                            {
                                "op": "eq",
                                "attr_name": "id",
                                "value": "1"
                            },
                        ]
                    }
                ]
            }
        ]
    }

    filter_, errors = parse_filter(
        '\tuserName   eq \n"bjen  sen" '
        'and '
        '('
        '\t  name.formatted ne "Craz\ny" '
        'or (\tnot urn:ietf:params:scim:schemas:core:2.0:User:nickName   co "b\t\tj" and id eq 1)\n\n'
        ')'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_basic_complex_attribute_filter_is_parsed():
    expected = {
        "op": "complex",
        "attr_name": "emails",
        "sub_op": {
            "op": "eq",
            "attr_name": "type",
            "value": '"work"',
        }
    }

    filter_, errors = parse_filter('emails[type eq "work"]')

    assert errors == []
    assert to_dict(filter_) == expected


def test_complex_attribute_filter_with_logical_operators_is_parsed():
    expected = {
        "op": "complex",
        "attr_name": "emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "eq",
                    "attr_name": "type",
                    "value": '"work"',
                },
                {
                    "op": "co",
                    "attr_name": "value",
                    "value": '"@example.com"',
                },
            ]
        }
    }

    filter_, errors = parse_filter('emails[type eq "work" and value co "@example.com"]')

    assert errors == []
    assert to_dict(filter_) == expected


def test_complex_attribute_filter_with_logical_operators_and_groups_is_parsed():
    expected = {
        "op": "complex",
        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr_name": "type",
                            "value": '"work"',
                        },
                        {
                            "op": "pr",
                            "attr_name": "emails.primary",
                        },
                    ]
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr_name": "value",
                            "value": '"@example.com"',
                        },
                        {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails.display",
                            "value": '"@example.com"',
                        },
                    ]
                }
            ]
        }
    }

    filter_, errors = parse_filter(
        'urn:ietf:params:scim:schemas:core:2.0:User:emails['
        '(type eq "work" or emails.primary pr) and '
        '(value co "@example.com" or urn:ietf:params:scim:schemas:core:2.0:User:emails.display co "@example.com")'
        ']'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_any_sequence_of_whitespace_characters_has_no_influence_on_complex_attribute_filter():
    expected = {
        "op": "complex",
        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr_name": "type",
                            "value": '"work"',
                        },
                        {
                            "op": "pr",
                            "attr_name": "emails.primary",
                        },
                    ]
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr_name": "value",
                            "value": '"@ex am\nple.com"',
                        },
                        {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails.display",
                            "value": '"@example\t.com"',
                        },
                    ]
                }
            ]
        }
    }

    filter_, errors = parse_filter(
        ' \turn:ietf:params:scim:schemas:core:2.0:User:emails[  '
        '('
        'type \neq "work" or\t\t emails.primary pr'
        ') \tand\n '
        '(  '
        'value co "@ex am\nple.com" or '
        'urn:ietf:params:scim:schemas:core:2.0:User:emails.display co "@example\t.com"'
        ')'
        ']'
    )

    assert errors == []
    assert to_dict(filter_) == expected


def test_gargantuan_filter():
    expected = {
        "op": "and",
        "sub_ops": [
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"'
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "name.formatted",
                        "value": '"Crazy"',
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:nickName",
                                    "value": '"bj"'
                                },
                             },
                            {
                                "op": "eq",
                                "attr_name": "id",
                                "value": "1"
                            },
                        ]
                    }
                ]
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "eq",
                                            "attr_name": "type",
                                            "value": '"work"',
                                        },
                                        {
                                            "op": "pr",
                                            "attr_name": "emails.primary",
                                        },
                                    ]
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr_name": "value",
                                            "value": '"@example.com"',
                                        },
                                        {
                                            "op": "co",
                                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:emails.display",
                                            "value": '"@example.com"',
                                        },
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "op": "complex",
                        "attr_name": "ims",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "eq",
                                            "attr_name": "type",
                                            "value": '"work"',
                                        },
                                        {
                                            "op": "pr",
                                            "attr_name": "emails.primary",
                                        },
                                    ]
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr_name": "value",
                                            "value": '"@example.com"',
                                        },
                                        {
                                            "op": "co",
                                            "attr_name": "display",
                                            "value": '"@example.com"',
                                        },
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    filter_, errors = parse_filter(
        'userName eq "bjensen" and '
        '('
        'name.formatted ne "Crazy" or '
        '(not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj" and id eq 1)'
        ') and '
        '('
        'urn:ietf:params:scim:schemas:core:2.0:User:emails['
        '(type eq "work" or emails.primary pr) and '
        '(value co "@example.com" or urn:ietf:params:scim:schemas:core:2.0:User:emails.display co "@example.com")'
        '] or '
        'ims['
        '(type eq "work" or emails.primary pr) and '
        '(value co "@example.com" or display co "@example.com")'
        ']'
        ')'
    )

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "bjensen"',
            {
                "op": "eq",
                "attr_name": "userName",
                "value": '"bjensen"',
            },
        ),
        (
            'name.familyName co "O\'Malley"',
            {
                "op": "co",
                "attr_name": "name.familyName",
                "value": '"O\'Malley"',
            },
        ),
        (
            'userName sw "J"',
            {
                "op": "sw",
                "attr_name": "userName",
                "value": '"J"',
            },
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:userName sw "J"',
            {
                "op": "sw",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                "value": '"J"',
            },
        ),
        (
            'title pr',
            {
                "op": "pr",
                "attr_name": "title",
            },
        ),
        (
            'meta.lastModified gt "2011-05-13T04:42:34Z"',
            {
                "op": "gt",
                "attr_name": "meta.lastModified",
                "value": '"2011-05-13T04:42:34Z"',
            },
        ),
        (
            'meta.lastModified ge "2011-05-13T04:42:34Z"',
            {
                "op": "ge",
                "attr_name": "meta.lastModified",
                "value": '"2011-05-13T04:42:34Z"',
            },
        ),
        (
            'meta.lastModified lt "2011-05-13T04:42:34Z"',
            {
                "op": "lt",
                "attr_name": "meta.lastModified",
                "value": '"2011-05-13T04:42:34Z"',
            },
        ),
        (
            'meta.lastModified le "2011-05-13T04:42:34Z"',
            {
                "op": "le",
                "attr_name": "meta.lastModified",
                "value": '"2011-05-13T04:42:34Z"',
            },
        ),
        (
            'title pr and userType eq "Employee"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "pr",
                        "attr_name": "title",
                    },
                    {
                        "op": "eq",
                        "attr_name": "userType",
                        "value": '"Employee"',
                    }
                ]
            },
        ),
        (
            'title pr or userType eq "Intern"',
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "pr",
                        "attr_name": "title",
                    },
                    {
                        "op": "eq",
                        "attr_name": "userType",
                        "value": '"Intern"',
                    }
                ]
            },
        ),
        (
            'schemas eq "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"',
            {
                "op": "eq",
                "attr_name": "schemas",
                "value": '"urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"',
            },
        ),
        (
            'userType eq "Employee" and (emails co "example.com" or emails.value co "example.org")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userType",
                        "value": '"Employee"',
                    },
                    {
                        "op": "or",
                        "sub_ops": [
                            {
                                "op": "co",
                                "attr_name": "emails",
                                "value": '"example.com"',
                            },
                            {
                                "op": "co",
                                "attr_name": "emails.value",
                                "value": '"example.org"',
                            },
                        ],
                    }
                ]
            },
        ),
        (
            'userType ne "Employee" and not (emails co "example.com" or emails.value co "example.org")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "ne",
                        "attr_name": "userType",
                        "value": '"Employee"',
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "or",
                            "sub_ops": [
                                {
                                    "op": "co",
                                    "attr_name": "emails",
                                    "value": '"example.com"',
                                },
                                {
                                    "op": "co",
                                    "attr_name": "emails.value",
                                    "value": '"example.org"',
                                },
                            ],
                        }
                    },
                ]
            },
        ),
        (
            'userType eq "Employee" and (emails.type eq "work")',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userType",
                        "value": '"Employee"',
                    },
                    {
                        "op": "eq",
                        "attr_name": "emails.type",
                        "value": '"work"',
                    },
                ]
            },
        ),
        (
            'userType eq "Employee" and emails[type eq "work" and value co "@example.com"]',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userType",
                        "value": '"Employee"',
                    },
                    {
                        "op": "complex",
                        "attr_name": "emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr_name": "type",
                                    "value": '"work"',
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
                                    "value": '"@example.com"',
                                },
                            ],
                        }
                    }
                ]
            },
        ),
        (
            'emails[type eq "work" and value co "@example.com"] or ims[type eq "xmpp" and value co "@foo.com"]',
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr_name": "type",
                                    "value": '"work"',
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
                                    "value": '"@example.com"',
                                },
                            ],
                        }
                    },
                    {
                        "op": "complex",
                        "attr_name": "ims",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr_name": "type",
                                    "value": '"xmpp"',
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
                                    "value": '"@foo.com"',
                                },
                            ],
                        }
                    }
                ]
            },
        )
    )
)
def test_rfc_7644_exemplary_filter(filter_exp, expected):
    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_codes"),
    (
        ('userName eq "user123" and (id eq 1 or display co "user"', [100]),
        ('userName eq "user123" and (id eq 1 or display co "use)r"', [100]),
        ('userName eq "user123" and id eq 1 or display co "user")', [101]),
        ('userName eq "user(123" and id eq 1 or display co "user")', [101]),
        ('userName eq "user123") and (id eq 1 or display co "user"', [101, 100]),
        ('userName eq "user(123") and (id eq 1 or display co "use)r"', [101, 100]),
        ('userName eq "user123") and (id eq 1 or display co "user") or (id eq 2 or display co "user"', [101, 100]),
        ('userName eq "user123") and ((id eq 1 or display co "user") or (id eq 2 or display co "user")', [101, 100]),
        ('userName eq "user123" and (not (id eq 1 or display co "user")', [100]),
        ('userName eq "user123" and not (id eq 1 or display co "user"))', [101]),
        ('emails[type eq "work" and (display co "@example.com" or value co "@example"]', [100]),
        ('emails[type eq "work") and (display co "@example.com" or value co "@example"]', [101, 100]),
        ('emails[type eq "work") and display co "@example.com" or value co "@example"]', [101]),

    )
)
def test_number_of_group_brackets_must_match(filter_exp, expected_error_codes):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_codes)
    for error, expected_error_code in zip(errors, expected_error_codes):
        assert error.code == expected_error_code


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use(r123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"use(r123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"us)er"'
                    }
                ]
            }
        ),
        (
            'userName eq "use(r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"use(r123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"user"'
                    }
                ]
            }
        ),
        (
            'userName eq "user123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"user123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"us)er"'
                    }
                ]
            }
        ),
    )
)
def test_group_bracket_characters_are_ignored_when_inside_string_value(filter_exp, expected):
    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_codes"),
    (
        ('emails[type eq "work" and display co "@example.com" or value co "@example"', [102]),
        ('emails type eq "work" and display co "@example.com" or value co "@example"]', [103]),
        ('emails[type eq "work" and ims[type eq "work"', [109]),
        ('emails[type eq "work"] and ims[type eq "work"', [102]),
        ('emails type eq "work"] and ims type eq "work"]', [103, 103]),
    )
)
def test_number_of_complex_attribute_brackets_must_match(filter_exp, expected_error_codes):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_codes)
    for error, expected_error_code in zip(errors, expected_error_codes):
        assert error.code == expected_error_code


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use[r123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"use[r123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"us]er"'
                    }
                ]
            }
        ),
        (
            'userName eq "use[r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"use[r123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"user"'
                    }
                ]
            }
        ),
        (
            'userName eq "user123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "eq",
                        "attr_name": "userName",
                        "value": '"user123"'
                    },
                    {
                        "op": "co",
                        "attr_name": "display",
                        "value": '"us]er"'
                    }
                ]
            }
        ),
    )
)
def test_complex_attribute_bracket_characters_are_ignored_when_inside_string_value(filter_exp, expected):
    filter_, errors = parse_filter(filter_exp)

    assert errors == []
    assert to_dict(filter_) == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_codes", "expected_error_contexts"),
    (
        (
            'userName eq "user123" and',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'userName eq "user123" and',
                }
            ]
        ),
        (
            ' and userName eq "user123"',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'and userName eq "user123"',
                }
            ]
        ),
        (
            'id eq 1 and and userName eq "user123"',
            [104, 104],
            [
                {
                    "operator": "and",
                    "expression": 'id eq 1 and',
                },
                {
                    "operator": "and",
                    "expression": 'and userName eq "user123"',
                }
            ]
        ),
        (
            'id eq 1 and userName eq "user123" and',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'userName eq "user123" and',
                }
            ]
        ),
        (
            'emails[type eq "work" and ]',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'type eq "work" and',
                }
            ]
        ),
        (
            'emails[ and type eq "work"]',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'and type eq "work"',
                }
            ]
        ),
        (
            'emails[ and type eq "work" and]',
            [104, 104],
            [
                {
                    "operator": "and",
                    "expression": 'and type eq "work"',
                },
                {
                    "operator": "and",
                    "expression": 'type eq "work" and',
                }
            ]
        ),
        (
            'and emails[ and type eq "work" and]',
            [104, 104, 104],
            [
                {
                    "operator": "and",
                    "expression": 'and emails[ and type eq "work" and]',
                },
                {
                    "operator": "and",
                    "expression": 'and type eq "work"',
                },
                {
                    "operator": "and",
                    "expression": 'type eq "work" and',
                }
            ]
        ),
        (
            'userName eq "user123" or',
            [104],
            [
                {
                    "operator": "or",
                    "expression": 'userName eq "user123" or',
                }
            ]
        ),
        (
            ' or userName eq "user123"',
            [104],
            [
                {
                    "operator": "or",
                    "expression": 'or userName eq "user123"',
                }
            ]
        ),
        (
            'id eq 1 or or userName eq "user123"',
            [104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'id eq 1 or',
                },
                {
                    "operator": "or",
                    "expression": 'or userName eq "user123"',
                }
            ]
        ),
        (
            'id eq 1 or userName eq "user123" or',
            [104],
            [
                {
                    "operator": "or",
                    "expression": 'userName eq "user123" or',
                }
            ]
        ),
        (
            'emails[type eq "work" or ]',
            [104],
            [
                {
                    "operator": "or",
                    "expression": 'type eq "work" or',
                }
            ]
        ),
        (
            'emails[ or type eq "work"]',
            [104],
            [
                {
                    "operator": "or",
                    "expression": 'or type eq "work"',
                }
            ]
        ),
        (
            'emails[ or type eq "work" or]',
            [104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'or type eq "work"',
                },
                {
                    "operator": "or",
                    "expression": 'type eq "work" or',
                }
            ]
        ),
        (
            'or emails[ or type eq "work" or]',
            [104, 104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'or emails[ or type eq "work" or]',
                },
                {
                    "operator": "or",
                    "expression": 'or type eq "work"',
                },
                {
                    "operator": "or",
                    "expression": 'type eq "work" or',
                }
            ]
        ),
        (
            'emails[ or type eq "work" and]',
            [104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'or type eq "work" and',
                },
                {
                    "operator": "and",
                    "expression": 'type eq "work" and',
                }
            ]
        ),
        (
            'or emails[ and type eq "work" or]',
            [104, 104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'or emails[ and type eq "work" or]',
                },
                {
                    "operator": "or",
                    "expression": 'and type eq "work" or',
                },
                {
                    "operator": "and",
                    "expression": 'and type eq "work"',
                },
            ]
        ),
        (
            'userName eq "user123" or (id eq 1 and)',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'id eq 1 and',
                }
            ]
        ),
        (
            'userName eq "user123" or (and id eq 1)',
            [104],
            [
                {
                    "operator": "and",
                    "expression": 'and id eq 1',
                }
            ]
        ),
        (
            'userName eq "user123" or (and id eq 1 or )',
            [104, 104],
            [
                {
                    "operator": "or",
                    "expression": 'and id eq 1 or',
                },
                {
                    "operator": "and",
                    "expression": 'and id eq 1',
                }
            ]
        ),
        (
            'userName eq "user123" or (and id eq 1 or ) and ',
            [104, 104, 104],
            [
                {
                    "operator": "and",
                    "expression": '(and id eq 1 or ) and',
                },
                {
                    "operator": "or",
                    "expression": 'and id eq 1 or',
                },
                {
                    "operator": "and",
                    "expression": 'and id eq 1',
                }
            ]
        ),
    )
)
def test_missing_operand_for_operator_causes_parsing_errors(
    filter_exp, expected_error_codes, expected_error_contexts
):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_codes)
    for error, code, context in zip(errors, expected_error_codes, expected_error_contexts):
        assert error.code == code
        assert error.context == context


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_contexts"),
    (
        (
            "apple banana",
            [
                {
                    "operator_type": "unary",
                    "operator": "banana",
                    "expression": "apple banana",
                }
            ]
        ),
        (
            "apple banana pear",
            [
                {
                    "operator_type": "binary",
                    "operator": "banana",
                    "expression": "apple banana pear",
                }
            ]
        ),
        (
            "(a b c) or (c d e)",
            [
                {
                    "operator_type": "binary",
                    "operator": "b",
                    "expression": "a b c"
                },
                {
                    "operator_type": "binary",
                    "operator": "d",
                    "expression": "c d e"
                }
            ]
        ),
        (
            "(a b) and emails[c d e or g h]",
            [
                {
                    "operator_type": "unary",
                    "operator": "b",
                    "expression": "a b"
                },
                {
                    "operator_type": "binary",
                    "operator": "d",
                    "expression": "c d e"
                },
                {
                    "operator_type": "unary",
                    "operator": "h",
                    "expression": "g h"
                }
            ]
        )
    )
)
def test_unknown_operator_causes_parsing_errors(
    filter_exp, expected_error_contexts
):
    filter_, errors = parse_filter(filter_exp)

    assert len(errors) == len(expected_error_contexts)
    for error, expected_context in zip(errors, expected_error_contexts):
        assert error.code == 105
        assert error.context == expected_context

    assert filter_ is None


def test_putting_complex_attribute_operator_inside_other_complex_attribute_operator_fails():
    filter_, errors = parse_filter('emails[type eq work and phones[type eq "home"]]')

    assert filter_ is None
    assert errors[0].code == 109


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_contexts"),
    (
        (
            'emai..ls[type eq "work"]',
            [
                {
                    "attribute": "emai..ls",
                },
            ]
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:emai..ls[type eq "work"]',
            [
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:emai..ls",
                },
            ]
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:emails.bla.bla[type eq "work"]',
            [
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:emails.bla.bla",
                },
            ]
        ),
        (
            'user..name eq "John Smith"',
            [
                {
                    "attribute": "user..name",
                },
            ]
        ),
        (
            'user..name pr',
            [
                {
                    "attribute": "user..name",
                },
            ]
        ),
        (
            'user..name eq "John Smith" and very.first.name eq "John"',
            [
                {
                    "attribute": "user..name",
                },
                {
                    "attribute": "very.first.name",
                }
            ]
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:user..name eq "John Smith"',
            [
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                },
            ]
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:user..name pr',
            [
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                },
            ]
        ),
        (
            (
                'urn:ietf:params:scim:schemas:core:2.0:User:user..name eq "John Smith" '
                'and urn:ietf:params:scim:schemas:core:2.0:User:very.first.name eq "John"'
            ),
            [
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                },
                {
                    "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:very.first.name",
                }
            ]
        ),
    )
)
def test_attribute_name_must_comform_abnf_rules(filter_exp, expected_error_contexts):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_contexts)
    for error, expected_error_context in zip(errors, expected_error_contexts):
        assert error.code == 111
        assert error.context == expected_error_context


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_contexts"),
    (
        (
            "emails[]",
            [
                {
                    "attribute": "emails",
                    "expression_position": 0,
                }
            ]
        ),
        (
            'emails[type eq "work"] and ims[]',
            [
                {
                    "attribute": "ims",
                    "expression_position": 27,
                }
            ]
        ),
        (
            'emails[] and ims[]',
            [
                {
                    "attribute": "emails",
                    "expression_position": 0,
                },
                {
                    "attribute": "ims",
                    "expression_position": 13,
                }
            ]
        ),
    )
)
def test_lack_of_expression_inside_complex_attribute_is_discovered(
    filter_exp, expected_error_contexts
):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_contexts)
    for error, expected_error_context in zip(errors, expected_error_contexts):
        assert error.code == 110
        assert error.context == expected_error_context


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_contexts"),
    (
        (
            '[type eq "work"]',
            [
                {
                    "expression": '[type eq "work"]',
                }
            ]
        ),
        (
            '[type eq "work"] and [type eq "home"]',
            [
                {
                    "expression": '[type eq "work"]',
                },
                {
                    "expression": '[type eq "home"]',
                }
            ]
        ),
        (
            'emails[type eq "work"] and [type eq "home"]',
            [
                {
                    "expression": '[type eq "home"]',
                }
            ]
        ),
    )
)
def test_lack_of_top_level_complex_attribute_name_is_discovered(
    filter_exp, expected_error_contexts
):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_contexts)
    for error, expected_error_context in zip(errors, expected_error_contexts):
        assert error.code == 108
        assert error.context == expected_error_context


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[type eq "work" and ims[type eq "home"]]',
        'emails[type eq "work"] and ims[type eq "home" and phones[type eq "work"]]',
    )
)
def test_presence_of_complex_attribute_inside_other_complex_attribute_is_discovered(filter_exp):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == 1
    assert errors[0].code == 109


@pytest.mark.parametrize(
    ("filter_exp", "expected_error_codes"),
    (
        (
            "",
            [107]
        ),
        (
            "()",
            [107]
        ),
        (
            'userName eq "John" and ()',
            [107]
        ),
        (
            '() and userName eq "John"',
            [107]
        ),
        (
            '() or userName eq "John" and ()',
            [107, 107]
        ),
        (
            'emails[type eq "work" and ()]',
            [107]
        ),
        (
            'emails[() and type eq "work"]',
            [107]
        ),
        (
            'emails[() or type eq "work" and ()]',
            [107, 107]
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()]',
            [107, 107]
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()] and ()',
            [107, 107, 107]
        ),
        (
            '() or userName eq "John" and emails[() or type eq "work" and ()] and ()',
            [107, 107, 107, 107]
        ),
    )
)
def test_no_expression_is_discovered(filter_exp, expected_error_codes):
    filter_, errors = parse_filter(filter_exp)

    assert filter_ is None
    assert len(errors) == len(expected_error_codes)
    for error, expected_error_code in zip(errors, expected_error_codes):
        assert error.code == expected_error_code


@pytest.mark.parametrize(
    "filter_exp",
    (
        'userName EQ "John"',
        'userName Eq "John"',
        'userName eQ "John"',
        'userName PR',
        'userName pR',
        'userName Pr'
    )
)
def test_operators_are_case_insensitive(filter_exp):
    filter_, errors = parse_filter(filter_exp)

    assert not errors
    assert filter_ is not None
