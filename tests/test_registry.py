import pytest

from src.assets.schemas import User
from src.data.operator import Equal, Present
from src.data.schemas import ResourceSchema
from src.registry import (
    register_binary_operator,
    register_resource_schema,
    register_unary_operator,
)


def test_runtime_error_is_raised_if_registering_same_resource_twice():
    with pytest.raises(RuntimeError, match="resource '.*' already registered"):
        register_resource_schema(User)


def test_runtime_error_is_raised_if_registering_same_schema_twice():
    with pytest.raises(RuntimeError, match="schema '.*' already registered"):
        register_resource_schema(
            ResourceSchema(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                name="SomethingDifferent",
            )
        )


def test_runtime_error_is_raised_if_binary_operator_is_registered_twice():
    with pytest.raises(RuntimeError, match="binary operator '.*' already registered"):
        register_binary_operator(Equal)


def test_runtime_error_is_raised_if_unary_operator_is_registered_twice():
    with pytest.raises(RuntimeError, match="unary operator '.*' already registered"):
        register_unary_operator(Present)
