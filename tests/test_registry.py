from typing import Any

import pytest

from scimpler.data import ResourceSchema
from scimpler.data.operator import BinaryAttributeOperator, UnaryAttributeOperator


def test_runtime_error_is_raised_if_registering_same_resource_name_but_different_endpoint(
    user_schema
):
    class FakeUserResource(ResourceSchema):
        name = "User"
        endpoint = "/FakeUsers"

    with pytest.raises(
        RuntimeError,
        match="resource 'User' already defined for different endpoint '/Users'",
    ):
        FakeUserResource()


def test_runtime_error_is_raised_if_provided_different_implementation_for_same_unary_operator():
    with pytest.raises(
        RuntimeError,
        match="different implementation for unary operator 'pr' already provided"
    ):
        class FakePresent(UnaryAttributeOperator):
            op = "pr"
            supported_scim_types = {"string"}
            supported_types = {str}

            @staticmethod
            def operator(value: Any) -> bool:
                return True


def test_runtime_error_is_raised_if_provided_different_implementation_for_same_binary_operator():
    with pytest.raises(
        RuntimeError,
        match="different implementation for binary operator 'eq' already provided"
    ):
        class FakeEqual(BinaryAttributeOperator):
            op = "eq"
            supported_scim_types = {"string"}
            supported_types = {str}

            @staticmethod
            def operator(attr_value: Any, op_value: Any) -> bool:
                return attr_value != op_value
