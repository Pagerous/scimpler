import pytest

from src.parser.parameters.filter.filter import parse_filter


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("operator", ("eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"))
def test_parse_basic_binary_attribute_filter(attr_name, operator):
    expected = {"op": operator, "attr_name": attr_name.lower(), "value": "bjensen"}
    filter_exp = f'{attr_name} {operator} "bjensen"'

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    "full_attr_name",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("operator", ("eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"))
def test_parse_basic_binary_complex_attribute_filter(full_attr_name, operator):
    sub_attr_name, attr_name = full_attr_name[::-1].split(".", 1)
    attr_name = attr_name[::-1]
    sub_attr_name = sub_attr_name[::-1]
    expected = {
        "op": "complex",
        "attr_name": attr_name.lower(),
        "sub_op": {
            "op": operator,
            "attr_name": sub_attr_name.lower(),
            "value": "bjensen",
        },
    }
    filter_exp = f'{full_attr_name} {operator} "bjensen"'

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("operator", ("pr",))
def test_parse_basic_unary_attribute_filter(attr_name, operator):
    expected = {
        "op": operator,
        "attr_name": attr_name.lower(),
    }
    filter_exp = f"{attr_name} {operator}"

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    "full_attr_name",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("operator", ("pr",))
def test_parse_basic_unary_attribute_filter_with_complex_attribute(full_attr_name, operator):
    sub_attr_name, attr_name = full_attr_name[::-1].split(".", 1)
    attr_name = attr_name[::-1]
    sub_attr_name = sub_attr_name[::-1]
    expected = {
        "op": "complex",
        "attr_name": attr_name.lower(),
        "sub_op": {
            "op": operator,
            "attr_name": sub_attr_name.lower(),
        },
    }
    filter_exp = f"{full_attr_name} {operator}"

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
    ),
)
@pytest.mark.parametrize("sequence", ("  ", "\t\t", "\n", " \t", "\t ", "\n\n", " \n", "\n "))
def test_any_sequence_of_whitespaces_between_tokens_has_no_influence_on_filter(attr_name, sequence):
    expected = {"op": "eq", "attr_name": attr_name.lower(), "value": f"bjen{sequence}sen"}
    filter_exp = f'{attr_name}{sequence}{sequence}eq{sequence}"bjen{sequence}sen"'

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    "full_attr_name",
    (
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
    ),
)
@pytest.mark.parametrize("sequence", ("  ", "\t\t", "\n", " \t", "\t ", "\n\n", " \n", "\n "))
def test_any_sequence_of_whitespaces_between_tokens_has_no_influence_on_filter_with_complex_attr(
    full_attr_name, sequence
):
    sub_attr_name, attr_name = full_attr_name[::-1].split(".", 1)
    attr_name = attr_name[::-1]
    sub_attr_name = sub_attr_name[::-1]

    expected = {
        "op": "complex",
        "attr_name": attr_name.lower(),
        "sub_op": {
            "op": "eq",
            "attr_name": sub_attr_name.lower(),
            "value": f"bjen{sequence}sen",
        },
    }

    filter_exp = f'{full_attr_name}{sequence}{sequence}eq{sequence}"bjen{sequence}sen"'

    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


def test_basic_filters_can_be_combined_with_and_operator():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjensen"},
            {
                "op": "complex",
                "attr_name": "name",
                "sub_op": {"op": "ne", "attr_name": "formatted", "value": "Crazy"},
            },
            {
                "op": "co",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:nickname",
                "value": "bj",
            },
        ],
    }

    filter_, issues = parse_filter(
        'userName eq "bjensen" '
        'and name.formatted ne "Crazy" '
        'and urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_basic_filters_can_be_combined_with_or_operator():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjensen"},
            {
                "op": "complex",
                "attr_name": "name",
                "sub_op": {"op": "ne", "attr_name": "formatted", "value": "Crazy"},
            },
            {
                "op": "co",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:nickname",
                "value": "bj",
            },
        ],
    }

    filter_, issues = parse_filter(
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'or urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_basic_filter_can_be_combined_with_not_operator():
    expected = {
        "op": "not",
        "sub_op": {
            "op": "eq",
            "attr_name": "username",
            "value": "bjensen",
        },
    }

    filter_, issues = parse_filter('not userName eq "bjensen"')

    assert not issues
    assert filter_.to_dict() == expected


def test_precedence_of_logical_operators_is_preserved():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjensen"},
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "name",
                        "sub_op": {
                            "op": "ne",
                            "attr_name": "formatted",
                            "value": "Crazy",
                        },
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:nickname",
                            "value": "bj",
                        },
                    },
                ],
            },
        ],
    }

    filter_, issues = parse_filter(
        'userName eq "bjensen" '
        'or name.formatted ne "Crazy" '
        'and not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj"'
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_whitespaces_between_tokens_with_logical_operators_has_no_influence_on_filter():
    expected = {
        "op": "or",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjen\tsen"},
            {
                "op": "and",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "name",
                        "sub_op": {
                            "op": "ne",
                            "attr_name": "formatted",
                            "value": "Craz\ny",
                        },
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "co",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:nickname",
                            "value": "b j",
                        },
                    },
                ],
            },
        ],
    }

    filter_, issues = parse_filter(
        'userName\t eq   "bjen\tsen" '
        'or\t  name.formatted    ne "Craz\ny" '
        'and \t\nnot  urn:ietf:params:scim:schemas:core:2.0:User:nickName co "b j"'
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_filter_groups_are_parsed():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjensen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "name",
                        "sub_op": {
                            "op": "ne",
                            "attr_name": "formatted",
                            "value": "Crazy",
                        },
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "urn:ietf:params:scim:schemas:core:2.0:"
                                    "user:nickname",
                                    "value": "bj",
                                },
                            },
                            {"op": "eq", "attr_name": "id", "value": 1},
                        ],
                    },
                ],
            },
        ],
    }

    filter_, issues = parse_filter(
        'userName eq "bjensen" '
        "and "
        "("
        'name.formatted ne "Crazy" '
        'or (not urn:ietf:params:scim:schemas:core:2.0:User:nickName co "bj" and id eq 1)'
        ")"
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_any_sequence_of_whitespaces_has_no_influence_on_filter_with_groups():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjen  sen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "name",
                        "sub_op": {
                            "op": "ne",
                            "attr_name": "formatted",
                            "value": "Craz\ny",
                        },
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": (
                                        "urn:ietf:params:scim:schemas:core:2.0:user:nickname"
                                    ),
                                    "value": "b\t\tj",
                                },
                            },
                            {"op": "eq", "attr_name": "id", "value": 1},
                        ],
                    },
                ],
            },
        ],
    }

    filter_, issues = parse_filter(
        '\tuserName   eq \n"bjen  sen" '
        "and "
        "("
        '\t  name.formatted ne "Craz\ny" '
        "or ("
        '\tnot urn:ietf:params:scim:schemas:core:2.0:User:nickName   co "b\t\tj" and id eq 1'
        ")\n\n"
        ")"
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_basic_complex_attribute_filter_is_parsed():
    expected = {
        "op": "complex",
        "attr_name": "emails",
        "sub_op": {
            "op": "eq",
            "attr_name": "type",
            "value": "work",
        },
    }

    filter_, issues = parse_filter('emails[type eq "work"]')

    assert not issues
    assert filter_.to_dict() == expected


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
                    "value": "work",
                },
                {
                    "op": "co",
                    "attr_name": "value",
                    "value": "@example.com",
                },
            ],
        },
    }

    filter_, issues = parse_filter('emails[type eq "work" and value co "@example.com"]')

    assert not issues
    assert filter_.to_dict() == expected


def test_complex_attribute_filter_with_logical_operators_and_groups_is_parsed():
    expected = {
        "op": "complex",
        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr_name": "type",
                            "value": "work",
                        },
                        {
                            "op": "pr",
                            "attr_name": "primary",
                        },
                    ],
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr_name": "value",
                            "value": "@example.com",
                        },
                        {
                            "op": "complex",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:emails",
                            "sub_op": {
                                "op": "co",
                                "attr_name": "display",
                                "value": "@example.com",
                            },
                        },
                    ],
                },
            ],
        },
    }

    filter_, issues = parse_filter(
        "urn:ietf:params:scim:schemas:core:2.0:User:emails["
        '(type eq "work" or primary pr) and '
        "("
        'value co "@example.com" or urn:ietf:params:scim:schemas:core:2.0:User:emails.display '
        'co "@example.com"'
        ")"
        "]"
    )

    assert not issues
    assert filter_.to_dict() == expected


def test_any_sequence_of_whitespace_characters_has_no_influence_on_complex_attribute_filter():
    expected = {
        "op": "complex",
        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:emails",
        "sub_op": {
            "op": "and",
            "sub_ops": [
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "eq",
                            "attr_name": "type",
                            "value": "work",
                        },
                        {
                            "op": "complex",
                            "attr_name": "emails",
                            "sub_op": {
                                "op": "pr",
                                "attr_name": "primary",
                            },
                        },
                    ],
                },
                {
                    "op": "or",
                    "sub_ops": [
                        {
                            "op": "co",
                            "attr_name": "value",
                            "value": "@ex am\nple.com",
                        },
                        {
                            "op": "complex",
                            "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:emails",
                            "sub_op": {
                                "op": "co",
                                "attr_name": "display",
                                "value": "@example\t.com",
                            },
                        },
                    ],
                },
            ],
        },
    }

    filter_, issues = parse_filter(
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

    assert not issues
    assert filter_.to_dict() == expected


def test_gargantuan_filter():
    expected = {
        "op": "and",
        "sub_ops": [
            {"op": "eq", "attr_name": "username", "value": "bjensen"},
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "name",
                        "sub_op": {
                            "op": "ne",
                            "attr_name": "formatted",
                            "value": "Crazy",
                        },
                    },
                    {
                        "op": "and",
                        "sub_ops": [
                            {
                                "op": "not",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "urn:ietf:params:scim:schemas:core:2.0:"
                                    "user:nickname",
                                    "value": "bj",
                                },
                            },
                            {"op": "eq", "attr_name": "id", "value": 1},
                        ],
                    },
                ],
            },
            {
                "op": "or",
                "sub_ops": [
                    {
                        "op": "complex",
                        "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "eq",
                                            "attr_name": "type",
                                            "value": "work",
                                        },
                                        {
                                            "op": "pr",
                                            "attr_name": "primary",
                                        },
                                    ],
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr_name": "value",
                                            "value": "@example.com",
                                        },
                                        {
                                            "op": "complex",
                                            "attr_name": (
                                                "urn:ietf:params:scim:schemas:core:2.0:user:emails"
                                            ),
                                            "sub_op": {
                                                "op": "co",
                                                "attr_name": "display",
                                                "value": "@example.com",
                                            },
                                        },
                                    ],
                                },
                            ],
                        },
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
                                            "value": "work",
                                        },
                                        {
                                            "op": "pr",
                                            "attr_name": "primary",
                                        },
                                    ],
                                },
                                {
                                    "op": "or",
                                    "sub_ops": [
                                        {
                                            "op": "co",
                                            "attr_name": "value",
                                            "value": "@example.com",
                                        },
                                        {
                                            "op": "co",
                                            "attr_name": "display",
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

    filter_, issues = parse_filter(
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

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "bjensen"',
            {
                "op": "eq",
                "attr_name": "username",
                "value": "bjensen",
            },
        ),
        (
            'name.familyName co "O\'Malley"',
            {
                "op": "complex",
                "attr_name": "name",
                "sub_op": {
                    "op": "co",
                    "attr_name": "familyname",
                    "value": "O'Malley",
                },
            },
        ),
        (
            'userName sw "J"',
            {
                "op": "sw",
                "attr_name": "username",
                "value": "J",
            },
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:userName sw "J"',
            {
                "op": "sw",
                "attr_name": "urn:ietf:params:scim:schemas:core:2.0:user:username",
                "value": "J",
            },
        ),
        (
            "title pr",
            {
                "op": "pr",
                "attr_name": "title",
            },
        ),
        (
            'meta.lastModified gt "2011-05-13T04:42:34Z"',
            {
                "op": "complex",
                "attr_name": "meta",
                "sub_op": {
                    "op": "gt",
                    "attr_name": "lastmodified",
                    "value": "2011-05-13T04:42:34Z",
                },
            },
        ),
        (
            'meta.lastModified ge "2011-05-13T04:42:34Z"',
            {
                "op": "complex",
                "attr_name": "meta",
                "sub_op": {
                    "op": "ge",
                    "attr_name": "lastmodified",
                    "value": "2011-05-13T04:42:34Z",
                },
            },
        ),
        (
            'meta.lastModified lt "2011-05-13T04:42:34Z"',
            {
                "op": "complex",
                "attr_name": "meta",
                "sub_op": {
                    "op": "lt",
                    "attr_name": "lastmodified",
                    "value": "2011-05-13T04:42:34Z",
                },
            },
        ),
        (
            'meta.lastModified le "2011-05-13T04:42:34Z"',
            {
                "op": "complex",
                "attr_name": "meta",
                "sub_op": {
                    "op": "le",
                    "attr_name": "lastmodified",
                    "value": "2011-05-13T04:42:34Z",
                },
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
                        "attr_name": "usertype",
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
                        "attr_name": "title",
                    },
                    {
                        "op": "eq",
                        "attr_name": "usertype",
                        "value": "Intern",
                    },
                ],
            },
        ),
        (
            'schemas eq "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"',
            {
                "op": "eq",
                "attr_name": "schemas",
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
                        "attr_name": "usertype",
                        "value": "Employee",
                    },
                    {
                        "op": "or",
                        "sub_ops": [
                            {
                                "op": "co",
                                "attr_name": "emails",
                                "value": "example.com",
                            },
                            {
                                "op": "complex",
                                "attr_name": "emails",
                                "sub_op": {
                                    "op": "co",
                                    "attr_name": "value",
                                    "value": "example.org",
                                },
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
                        "attr_name": "usertype",
                        "value": "Employee",
                    },
                    {
                        "op": "not",
                        "sub_op": {
                            "op": "or",
                            "sub_ops": [
                                {
                                    "op": "co",
                                    "attr_name": "emails",
                                    "value": "example.com",
                                },
                                {
                                    "op": "complex",
                                    "attr_name": "emails",
                                    "sub_op": {
                                        "op": "co",
                                        "attr_name": "value",
                                        "value": "example.org",
                                    },
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
                        "attr_name": "usertype",
                        "value": "Employee",
                    },
                    {
                        "op": "complex",
                        "attr_name": "emails",
                        "sub_op": {
                            "op": "eq",
                            "attr_name": "type",
                            "value": "work",
                        },
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
                        "attr_name": "usertype",
                        "value": "Employee",
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
                                    "value": "work",
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
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
                        "attr_name": "emails",
                        "sub_op": {
                            "op": "and",
                            "sub_ops": [
                                {
                                    "op": "eq",
                                    "attr_name": "type",
                                    "value": "work",
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
                                    "value": "@example.com",
                                },
                            ],
                        },
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
                                    "value": "xmpp",
                                },
                                {
                                    "op": "co",
                                    "attr_name": "value",
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
    filter_, issues = parse_filter(filter_exp)

    assert not issues
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
            {"_errors": [{"code": 101}]},
        ),
        (
            'userName eq "user(123" and id eq 1 or display co "user")',
            {"_errors": [{"code": 101}]},
        ),
        (
            'userName eq "user123") and (id eq 1 or display co "user"',
            {"_errors": [{"code": 101}, {"code": 100}]},
        ),
        (
            'userName eq "user(123") and (id eq 1 or display co "use)r"',
            {"_errors": [{"code": 101}, {"code": 100}]},
        ),
        (
            'userName eq "user123") and (id eq 1 or display co "user") '
            'or (id eq 2 or display co "user"',
            {"_errors": [{"code": 101}, {"code": 100}]},
        ),
        (
            'userName eq "user123") and ((id eq 1 or display co "user") '
            'or (id eq 2 or display co "user")',
            {"_errors": [{"code": 101}, {"code": 100}]},
        ),
        (
            'userName eq "user123" and (not (id eq 1 or display co "user")',
            {"_errors": [{"code": 100}]},
        ),
        (
            'userName eq "user123" and not (id eq 1 or display co "user"))',
            {"_errors": [{"code": 101}]},
        ),
        (
            'emails[type eq "work" and (display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 100}]},
        ),
        (
            'emails[type eq "work") and (display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 101}, {"code": 100}]},
        ),
        (
            'emails[type eq "work") and display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 101}]},
        ),
    ),
)
def test_number_of_group_brackets_must_match(filter_exp, expected_issues):
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use(r123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "use(r123"},
                    {"op": "co", "attr_name": "display", "value": "us)er"},
                ],
            },
        ),
        (
            'userName eq "use(r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "use(r123"},
                    {"op": "co", "attr_name": "display", "value": "user"},
                ],
            },
        ),
        (
            'userName eq "user123" and display co "us)er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "user123"},
                    {"op": "co", "attr_name": "display", "value": "us)er"},
                ],
            },
        ),
    ),
)
def test_group_bracket_characters_are_ignored_when_inside_string_value(filter_exp, expected):
    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'emails[type eq "work" and display co "@example.com" or value co "@example"',
            {"_errors": [{"code": 102}]},
        ),
        (
            'emails type eq "work" and display co "@example.com" or value co "@example"]',
            {"_errors": [{"code": 103}]},
        ),
        ('emails[type eq "work" and ims[type eq "work"', {"_errors": [{"code": 109}]}),
        ('emails[type eq "work"] and ims[type eq "work"', {"_errors": [{"code": 102}]}),
        (
            'emails type eq "work"] and ims type eq "work"]',
            {"_errors": [{"code": 103}, {"code": 103}]},
        ),
    ),
)
def test_number_of_complex_attribute_brackets_must_match(filter_exp, expected_issues):
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected"),
    (
        (
            'userName eq "use[r123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "use[r123"},
                    {"op": "co", "attr_name": "display", "value": "us]er"},
                ],
            },
        ),
        (
            'userName eq "use[r123" and display co "user"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "use[r123"},
                    {"op": "co", "attr_name": "display", "value": "user"},
                ],
            },
        ),
        (
            'userName eq "user123" and display co "us]er"',
            {
                "op": "and",
                "sub_ops": [
                    {"op": "eq", "attr_name": "username", "value": "user123"},
                    {"op": "co", "attr_name": "display", "value": "us]er"},
                ],
            },
        ),
    ),
)
def test_complex_attribute_bracket_characters_are_ignored_when_inside_string_value(
    filter_exp, expected
):
    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'userName eq "user123" and',
            {
                "_errors": [
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "and",
                            "expression": "id eq 1 and",
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "and",
                            "expression": 'and emails[ and type eq "work" and]',
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "and",
                            "expression": 'and type eq "work"',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": "id eq 1 or",
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work"',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'or emails[ or type eq "work" or]',
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work"',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'or type eq "work" and',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'or emails[ and type eq "work" or]',
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": 'and type eq "work" or',
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": "and id eq 1 or",
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
                        "context": {
                            "operator": "and",
                            "expression": "(and id eq 1 or ) and",
                        },
                    },
                    {
                        "code": 104,
                        "context": {
                            "operator": "or",
                            "expression": "and id eq 1 or",
                        },
                    },
                    {
                        "code": 104,
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
                        "code": 104,
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
                        "code": 104,
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
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "apple banana",
            {
                "_errors": [
                    {
                        "code": 105,
                        "context": {
                            "operator_type": "unary",
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
                        "code": 105,
                        "context": {
                            "operator_type": "binary",
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
                        "code": 105,
                        "context": {
                            "operator_type": "binary",
                            "operator": "b",
                            "expression": 'a b "c"',
                        },
                    },
                    {
                        "code": 105,
                        "context": {
                            "operator_type": "binary",
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
                        "code": 105,
                        "context": {
                            "operator_type": "unary",
                            "operator": "b",
                            "expression": "a b",
                        },
                    },
                    {
                        "code": 105,
                        "context": {
                            "operator_type": "binary",
                            "operator": "d",
                            "expression": 'c d "e"',
                        },
                    },
                    {
                        "code": 105,
                        "context": {
                            "operator_type": "unary",
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
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


def test_putting_complex_attribute_operator_inside_other_complex_attribute_operator_fails():
    expected_issues = {"_errors": [{"code": 109}]}
    filter_, issues = parse_filter('emails[type eq work and phones[type eq "home"]]')

    assert filter_ is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            'emai..ls[type eq "work"]',
            {"_errors": [{"code": 111, "context": {"attribute": "emai..ls"}}]},
        ),
        (
            'urn:ietf:params:scim:schemas:core:2.0:User:emai..ls[type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 111,
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
                        "code": 111,
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
                        "code": 111,
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
                        "code": 111,
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
                        "code": 111,
                        "context": {
                            "attribute": "user..name",
                        },
                    },
                    {
                        "code": 111,
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
                        "code": 111,
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
                        "code": 111,
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
                        "code": 111,
                        "context": {
                            "attribute": "urn:ietf:params:scim:schemas:core:2.0:User:user..name",
                        },
                    },
                    {
                        "code": 111,
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
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "emails[]",
            {
                "_errors": [
                    {
                        "code": 110,
                        "context": {
                            "attribute": "emails",
                            "expression_position": 0,
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
                        "code": 110,
                        "context": {
                            "attribute": "ims",
                            "expression_position": 27,
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
                        "code": 110,
                        "context": {
                            "attribute": "emails",
                            "expression_position": 0,
                        },
                    },
                    {
                        "code": 110,
                        "context": {
                            "attribute": "ims",
                            "expression_position": 13,
                        },
                    },
                ]
            },
        ),
    ),
)
def test_lack_of_expression_inside_complex_attribute_is_discovered(filter_exp, expected_issues):
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            '[type eq "work"]',
            {
                "_errors": [
                    {
                        "code": 111,
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
                        "code": 111,
                        "context": {"attribute": ""},
                    },
                    {
                        "code": 111,
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
                        "code": 111,
                        "context": {"attribute": ""},
                    }
                ]
            },
        ),
    ),
)
def test_lack_of_top_level_complex_attribute_name_is_discovered(filter_exp, expected_issues):
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


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
    expected_issues = {"_errors": [{"code": 109}]}
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        ("", {"_errors": [{"code": 107}]}),
        ("()", {"_errors": [{"code": 107}]}),
        ('userName eq "John" and ()', {"_errors": [{"code": 107}]}),
        ('() and userName eq "John"', {"_errors": [{"code": 107}]}),
        (
            '() or userName eq "John" and ()',
            {"_errors": [{"code": 107}, {"code": 107}]},
        ),
        ('emails[type eq "work" and ()]', {"_errors": [{"code": 107}]}),
        ('emails[() and type eq "work"]', {"_errors": [{"code": 107}]}),
        (
            'emails[() or type eq "work" and ()]',
            {"_errors": [{"code": 107}, {"code": 107}]},
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()]',
            {"_errors": [{"code": 107}, {"code": 107}]},
        ),
        (
            'userName eq "John" and emails[() or type eq "work" and ()] and ()',
            {"_errors": [{"code": 107}, {"code": 107}, {"code": 107}]},
        ),
        (
            '() or userName eq "John" and emails[() or type eq "work" and ()] and ()',
            {"_errors": [{"code": 107}, {"code": 107}, {"code": 107}, {"code": 107}]},
        ),
    ),
)
def test_no_expression_is_discovered(filter_exp, expected_issues):
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict() == expected_issues


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
    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_ is not None


@pytest.mark.parametrize(
    ("filter_exp", "expected_filter"),
    (
        (
            'attr eq "John"',
            {
                "op": "eq",
                "attr_name": "attr",
                "value": "John",
            },
        ),
        (
            "attr eq 1",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": 1,
            },
        ),
        (
            "attr eq 1.0",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": 1,
            },
        ),
        (
            "attr eq 1.2",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": 1.2,
            },
        ),
        (
            "attr eq false",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": False,
            },
        ),
        (
            "attr eq true",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": True,
            },
        ),
        (
            "attr eq null",
            {
                "op": "eq",
                "attr_name": "attr",
                "value": None,
            },
        ),
    ),
)
def test_operators_are_case_insensitive(filter_exp, expected_filter):
    filter_, issues = parse_filter(filter_exp)

    assert not issues
    assert filter_.to_dict() == expected_filter


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "userName eq blabla",
            {
                "_errors": [
                    {
                        "code": 112,
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
                        "code": 112,
                        "context": {
                            "value": "blabla",
                        },
                    },
                    {
                        "code": 112,
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
                        "code": 112,
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
                        "code": 112,
                        "context": {
                            "value": "blabla",
                        },
                    },
                    {
                        "code": 112,
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
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("filter_exp", "expected_issues"),
    (
        (
            "userName gt true",
            {
                "_errors": [
                    {
                        "code": 113,
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
                        "code": 113,
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
                        "code": 113,
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
                        "code": 113,
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
                        "code": 113,
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
                        "code": 113,
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
                        "code": 113,
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
    filter_, issues = parse_filter(filter_exp)

    assert filter_ is None
    assert issues.to_dict(ctx=True) == expected_issues
