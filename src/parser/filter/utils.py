from typing import Union

from src.parser.filter import operator as op


def to_dict(filter_: Union[op.LogicalOperator, op.AttributeOperator, op.ComplexAttributeOperator]):
    if isinstance(filter_, op.AttributeOperator):
        filter_dict = {
            "op": filter_.SCIM_OP,
            "attr_name": filter_.attr_name,
        }
        if isinstance(filter_, op.BinaryAttributeOperator):
            filter_dict["value"] = filter_.value
        return filter_dict

    if isinstance(filter_, op.ComplexAttributeOperator):
        return {
            "op": "complex",
            "attr_name": filter_.attr_name,
            "sub_op": to_dict(filter_.sub_operator)
        }

    if isinstance(filter_, op.Not):
        return {
            "op": filter_.SCIM_OP,
            "sub_op": to_dict(filter_.sub_operator),
        }

    if isinstance(filter_, op.MultiOperandLogicalOperator):
        return {
            "op": filter_.SCIM_OP,
            "sub_ops": [
                to_dict(sub_operator) for sub_operator in filter_.sub_operators
            ]
        }

    raise TypeError(f"unsupported filter type '{type(filter_).__name__}'")
