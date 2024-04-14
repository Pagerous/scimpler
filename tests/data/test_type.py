import base64
from datetime import datetime

import pytest

from src.data import type as at
from src.data.container import SCIMDataContainer


@pytest.mark.parametrize(
    ("input_value", "type_", "expected_issues"),
    (
        (
            1.0,
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
def test_validate_bad_type(input_value, type_, expected_issues):
    issues = type_.validate(input_value)

    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("input_value", "type_"),
    (
        (
            "123",
            at.String,
        ),
        (
            123,
            at.Integer,
        ),
        (
            1,
            at.Decimal,
        ),
        (
            1.2,
            at.Decimal,
        ),
        (
            True,
            at.Boolean,
        ),
        (
            "any:unique:resource:identifier",
            at.URIReference,
        ),
        (
            "Users",
            at.SCIMReference,
        ),
        (
            "https://www.example.com/absolute/url",
            at.ExternalReference,
        ),
        (
            base64.b64encode("blahblah".encode()).decode("utf-8"),
            at.Binary,
        ),
        (
            "2024-01-06T00:00:00",
            at.DateTime,
        ),
        (
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
            at.Complex,
        ),
    ),
)
def test_validate_correct_type(input_value, type_):
    issues = type_.validate(input_value)

    assert issues.to_dict(msg=True) == {}
