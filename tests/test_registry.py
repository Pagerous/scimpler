from datetime import datetime

import pytest

from src.assets.schemas import User
from src.data.operator import Equal, Present
from src.registry import (
    register_binary_operator,
    register_deserializer,
    register_resource_schema,
    register_serializer,
    register_unary_operator,
)


def test_runtime_error_is_raised_if_registering_same_schema_twice():
    with pytest.raises(RuntimeError, match="schema '.*' already registered"):
        register_resource_schema(User)


def test_runtime_error_is_raised_if_registering_serializer_for_unknown_scim_type():
    with pytest.raises(ValueError, match="not a valid SCIMType"):
        register_serializer("whatever", lambda val: val.upper())


def test_runtime_error_is_raised_if_serializer_is_registered_twice():
    def datetime_converter(val):
        return datetime.fromisoformat(val)

    register_serializer("dateTime", datetime_converter)

    with pytest.raises(
        RuntimeError, match=r"serializer for SCIMType\(dateTime\) already registered"
    ):
        register_serializer("dateTime", datetime_converter)


def test_runtime_error_is_raised_if_registering_deserializer_for_unknown_scim_type():
    with pytest.raises(ValueError, match="not a valid SCIMType"):
        register_deserializer("whatever", lambda val: val.upper())


def test_runtime_error_is_raised_if_deserializer_is_registered_twice():
    def datetime_converter(val):
        return datetime.isoformat(val)

    register_deserializer("dateTime", datetime_converter)

    with pytest.raises(
        RuntimeError, match=r"deserializer for SCIMType\(dateTime\) already registered"
    ):
        register_deserializer("dateTime", datetime_converter)


def test_runtime_error_is_raised_if_binary_operator_is_registered_twice():
    with pytest.raises(RuntimeError, match="binary operator '.*' already registered"):
        register_binary_operator(Equal)


def test_runtime_error_is_raised_if_unary_operator_is_registered_twice():
    with pytest.raises(RuntimeError, match="unary operator '.*' already registered"):
        register_unary_operator(Present)
