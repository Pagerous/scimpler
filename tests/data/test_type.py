import base64
from datetime import datetime

import pytest

from src.data import type as at
from src.data.container import SCIMDataContainer


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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "integer",
                            "provided": "string",
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
                            "expected": "integer",
                            "provided": "decimal",
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
                            "expected": "decimal",
                            "provided": "string",
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
                            "expected": "boolean",
                            "provided": "string",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        ("bad", at.Binary, {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}),
        (
            123,
            at.DateTime,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            "2022/05/05 12:34:56",
            at.DateTime,
            {"_errors": [{"code": 1, "context": {}}]},
        ),
        (
            123,
            at.Complex,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "complex",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
    ),
)
def test_parse_invalid(input_value, type_, expected_issues):
    actual, issues = type_.parse(input_value)

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
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "integer",
                            "provided": "string",
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
                            "expected": "integer",
                            "provided": "decimal",
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
                            "expected": "decimal",
                            "provided": "string",
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
                            "expected": "boolean",
                            "provided": "string",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
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
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        ("bad", at.Binary, {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}),
        (
            "2024-01-06T20:16:39.399319",
            at.DateTime,
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "datetime",
                            "provided": "string",
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
                        "code": 2,
                        "context": {
                            "expected": "complex",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
    ),
)
def test_dump_invalid(input_value, type_, expected_issues):
    actual, issues = type_.dump(input_value)

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
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
            at.Complex,
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
        ),
    ),
)
def test_parse_valid(input_value, type_, expected):
    actual, issues = type_.parse(input_value)

    assert actual == expected
    assert issues.to_dict(msg=True) == {}


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
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
            at.Complex,
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
        ),
    ),
)
def test_dump_valid(input_value, type_, expected):
    actual, issues = type_.dump(input_value)

    assert actual == expected
    assert issues.to_dict(msg=True) == {}
