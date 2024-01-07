import base64
from datetime import datetime

import pytest

from src.attributes import type as at


@pytest.mark.parametrize(
    ("input_value", "type_", "expected_issues"),
    (
        (
            123,
            at.String,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "string",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            at.Integer,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "integer",
                            "expected_type": "int",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            1.2,
            at.Integer,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "integer",
                            "expected_type": "int",
                            "provided_type": "float",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            at.Decimal,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "decimal",
                            "expected_type": "float",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            "Bad",
            at.Boolean,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "boolean",
                            "expected_type": "bool",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.URIReference,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.SCIMReference,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.ExternalReference,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            "/not/absolute/url",
            at.ExternalReference,
            {"_errors": [{"code": 8, "context": {"value": "/not/absolute/url"}}]},
        ),
        (
            123,
            at.Binary,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "binary",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        ("blahblah", at.Binary, {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}),
        (
            123,
            at.DateTime,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "dateTime",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            "2022/05/05 12:34:56",
            at.DateTime,
            {"_errors": [{"code": 4, "context": {"scim_type": "dateTime"}}]},
        ),
        (
            123,
            at.Complex,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "scim_type": "complex",
                            "expected_type": "dict",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            {"sub_attr_1": {}, "sub_attr_2": []},
            at.Complex,
            {
                "sub_attr_1": {
                    "_errors": [
                        {
                            "code": 5,
                            "context": {
                                "allowed_types": ["bool", "float", "int", "str"],
                                "provided_type": "dict",
                                "scim_type": "complex",
                            },
                        }
                    ]
                },
                "sub_attr_2": {
                    "_errors": [
                        {
                            "code": 5,
                            "context": {
                                "allowed_types": ["bool", "float", "int", "str"],
                                "provided_type": "list",
                                "scim_type": "complex",
                            },
                        }
                    ]
                },
            },
        ),
    ),
)
def test_parse_invalid(input_value, type_, expected_issues):
    actual, issues = type_.parse(input_value)

    assert not actual
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("input_value", "type_", "expected_issues"),
    (
        (
            123,
            at.String,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "string",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            at.Integer,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "integer",
                            "expected_type": "int",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            1.2,
            at.Integer,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "integer",
                            "expected_type": "int",
                            "provided_type": "float",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            at.Decimal,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "decimal",
                            "expected_type": "float",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            "Bad",
            at.Boolean,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "boolean",
                            "expected_type": "bool",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.URIReference,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.SCIMReference,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.ExternalReference,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "reference",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            "/not/absolute/url",
            at.ExternalReference,
            {"_errors": [{"code": 8, "context": {"value": "/not/absolute/url"}}]},
        ),
        (
            123,
            at.Binary,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "binary",
                            "expected_type": "str",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        ("blahblah", at.Binary, {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}),
        (
            "2024-01-06T20:16:39.399319",
            at.DateTime,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "dateTime",
                            "expected_type": "datetime",
                            "provided_type": "str",
                        },
                    }
                ]
            },
        ),
        (
            123,
            at.Complex,
            {
                "_errors": [
                    {
                        "code": 31,
                        "context": {
                            "scim_type": "complex",
                            "expected_type": "dict",
                            "provided_type": "int",
                        },
                    }
                ]
            },
        ),
        (
            {"sub_attr_1": {}, "sub_attr_2": []},
            at.Complex,
            {
                "sub_attr_1": {
                    "_errors": [
                        {
                            "code": 32,
                            "context": {
                                "allowed_types": ["bool", "datetime", "float", "int", "str"],
                                "provided_type": "dict",
                                "scim_type": "complex",
                            },
                        }
                    ]
                },
                "sub_attr_2": {
                    "_errors": [
                        {
                            "code": 32,
                            "context": {
                                "allowed_types": ["bool", "datetime", "float", "int", "str"],
                                "provided_type": "list",
                                "scim_type": "complex",
                            },
                        }
                    ]
                },
            },
        ),
    ),
)
def test_dump_invalid(input_value, type_, expected_issues):
    actual, issues = type_.dump(input_value)

    assert not actual
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("input_value", "type_", "expected"),
    (
        (
            "123",
            at.String,
            "123",
        ),
        (
            123,
            at.Integer,
            123,
        ),
        (
            1.0,
            at.Integer,
            1,
        ),
        (
            1,
            at.Decimal,
            1.0,
        ),
        (
            1.2,
            at.Decimal,
            1.2,
        ),
        (
            True,
            at.Boolean,
            True,
        ),
        (
            "any:unique:resource:identifier",
            at.URIReference,
            "any:unique:resource:identifier",
        ),
        (
            "Users",
            at.SCIMReference,
            "Users",
        ),
        (
            "https://www.example.com/absolute/url",
            at.ExternalReference,
            "https://www.example.com/absolute/url",
        ),
        (
            base64.b64encode("blahblah".encode()).decode("utf-8"),
            at.Binary,
            base64.b64encode("blahblah".encode()).decode("utf-8"),
        ),
        (
            "2024-01-06T00:00:00",
            at.DateTime,
            datetime(2024, 1, 6),
        ),
        (
            {"sub_attr_1": 1, "sub_attr_2": "2"},
            at.Complex,
            {"sub_attr_1": 1, "sub_attr_2": "2"},
        ),
    ),
)
def test_parse_valid(input_value, type_, expected):
    actual, issues = type_.parse(input_value)

    assert actual == expected
    assert issues.to_dict() == {}


@pytest.mark.parametrize(
    ("input_value", "type_", "expected"),
    (
        (
            "123",
            at.String,
            "123",
        ),
        (
            123,
            at.Integer,
            123,
        ),
        (
            1.0,
            at.Integer,
            1,
        ),
        (
            1,
            at.Decimal,
            1.0,
        ),
        (1.2, at.Decimal, 1.2),
        (
            True,
            at.Boolean,
            True,
        ),
        (
            "any:unique:resource:identifier",
            at.URIReference,
            "any:unique:resource:identifier",
        ),
        (
            "Users",
            at.SCIMReference,
            "Users",
        ),
        (
            "https://www.example.com/absolute/url",
            at.ExternalReference,
            "https://www.example.com/absolute/url",
        ),
        (
            base64.b64encode("blahblah".encode()).decode("utf-8"),
            at.Binary,
            base64.b64encode("blahblah".encode()).decode("utf-8"),
        ),
        (datetime(2024, 1, 6), at.DateTime, "2024-01-06T00:00:00"),
        (
            {"sub_attr_1": 1, "sub_attr_2": "2"},
            at.Complex,
            {"sub_attr_1": 1, "sub_attr_2": "2"},
        ),
    ),
)
def test_dump_valid(input_value, type_, expected):
    actual, issues = type_.dump(input_value)

    assert actual == expected
    assert issues.to_dict() == {}
