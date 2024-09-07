from typing import Any, Optional

import pytest

from scimpler.data import ScimData
from scimpler.data.operator import (
    AttributeOperator,
    BinaryAttributeOperator,
    TSchemaOrComplex,
    UnaryAttributeOperator,
)
from scimpler.data.schemas import BaseSchema, ResourceSchema


def test_runtime_error_is_raised_if_registering_same_resource_name_but_different_endpoint(
    user_schema,
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
        RuntimeError, match="different implementation for unary operator 'pr' already provided"
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
        RuntimeError, match="different implementation for binary operator 'eq' already provided"
    ):

        class FakeEqual(BinaryAttributeOperator):
            op = "eq"
            supported_scim_types = {"string"}
            supported_types = {str}

            @staticmethod
            def operator(attr_value: Any, op_value: Any) -> bool:
                return attr_value != op_value


def test_attempt_to_register_again_api_message_schema_fails():
    with pytest.raises(RuntimeError, match="schemas for SCIM API messages can not be overridden"):

        class FakeListResponseSchema(BaseSchema):
            schema = "urn:ietf:params:scim:api:messages:2.0:ListResponse"


def test_subclassing_attribute_operator_with_custom_class_fails():
    with pytest.raises(TypeError, match="custom subclassing of 'AttributeOperator' is forbidden"):

        class OtherAttributeOperator(AttributeOperator):
            def match(
                self,
                value: Optional[ScimData],
                schema_or_complex: TSchemaOrComplex,
            ) -> bool:
                return False
