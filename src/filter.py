import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, TypeAlias, Union

from src.data import operator as op
from src.data.container import AttrRep, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.utils import (
    OP_REGEX,
    decode_placeholders,
    deserialize_comparison_value,
    deserialize_placeholder,
    encode_strings,
    get_placeholder,
)

if TYPE_CHECKING:
    from src.data.schemas import BaseSchema

OR_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\bor\b\s*", flags=re.DOTALL)
AND_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\band\b\s*", flags=re.DOTALL)
NOT_LOGICAL_OPERATOR_REGEX = re.compile(r"\s*\bnot\b\s*(.*)", flags=re.DOTALL)
COMPLEX_OPERATOR_REGEX = re.compile(r"([\w:.]+)\[(.*?)]", flags=re.DOTALL)
GROUP_OPERATOR_REGEX = re.compile(r"\((?:[^()]|\([^()]*\))*\)", flags=re.DOTALL)

_UNARY_ATTR_OPERATORS = {
    "pr": op.Present,
}

_BINARY_ATTR_OPERATORS = {
    "eq": op.Equal,
    "ne": op.NotEqual,
    "co": op.Contains,
    "sw": op.StartsWith,
    "ew": op.EndsWith,
    "gt": op.GreaterThan,
    "ge": op.GreaterThanOrEqual,
    "lt": op.LesserThan,
    "le": op.LesserThanOrEqual,
}

_ALLOWED_VALUE_TYPES_FOR_BINARY_OPERATORS = {
    op.Equal: {int, float, str, bool, type(None)},
    op.NotEqual: {int, float, str, bool, type(None)},
    op.Contains: {str},
    op.StartsWith: {str},
    op.EndsWith: {str},
    op.GreaterThan: {str, int, float},
    op.GreaterThanOrEqual: {str, int, float},
    op.LesserThan: {str, int, float},
    op.LesserThanOrEqual: {str, int, float},
}

_AllowedOperandValues: TypeAlias = Union[str, bool, int, float, None]


_DeserializedOperator: TypeAlias = Union[
    op.AttributeOperator,
    op.LogicalOperator,
    op.ComplexAttributeOperator,
]


@dataclass
class _ValidatedComplexOperator:
    issues: ValidationIssues
    expression: str


@dataclass
class _ValidatedGroupOperator:
    issues: ValidationIssues
    expression: str


class Filter:
    def __init__(self, operator: _DeserializedOperator):
        self._operator = operator

    @property
    def operator(self) -> _DeserializedOperator:
        return self._operator

    @classmethod
    def validate(cls, filter_exp: str) -> ValidationIssues:
        issues = ValidationIssues()
        filter_exp, placeholders = encode_strings(filter_exp)
        bracket_open_index = None
        complex_attr_rep = ""
        filter_exp_iter_copy = filter_exp
        for i, char in enumerate(filter_exp_iter_copy):
            if (re.match(r"\w", char) or char in ":.") and bracket_open_index is None:
                complex_attr_rep += char
            elif char == "[":
                if bracket_open_index is not None:
                    issues.add_error(
                        issue=ValidationError.inner_complex_attribute_or_square_bracket(),
                        proceed=False,
                    )
                    break
                else:
                    bracket_open_index = i
            elif char == "]":
                if bracket_open_index is None:
                    issues.add_error(
                        issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                        proceed=False,
                    )
                else:
                    sub_ops_exp = filter_exp_iter_copy[bracket_open_index + 1 : i]
                    complex_attr_exp = f"{complex_attr_rep}[{sub_ops_exp}]"
                    issues_ = ValidationIssues()
                    if sub_ops_exp.strip() == "":
                        issues_.add_error(
                            issue=ValidationError.empty_complex_attribute_expression(
                                complex_attr_rep
                            ),
                            proceed=False,
                        )
                    try:
                        attr_rep = AttrRep.deserialize(complex_attr_rep)
                        if attr_rep.sub_attr:
                            issues_.add_error(
                                issue=ValidationError.complex_sub_attribute(
                                    attr=attr_rep.attr, sub_attr=attr_rep.sub_attr
                                ),
                                proceed=False,
                            )
                    except ValueError:
                        issues_.add_error(
                            issue=ValidationError.bad_attribute_name(complex_attr_rep),
                            proceed=False,
                        )
                    id_, placeholder = get_placeholder()
                    if not issues_.can_proceed():
                        placeholders[id_] = _ValidatedComplexOperator(
                            issues=issues_,
                            expression=complex_attr_exp,
                        )
                    else:
                        placeholders[id_] = _ValidatedComplexOperator(
                            issues=Filter._validate_operator(sub_ops_exp, placeholders),
                            expression=complex_attr_exp,
                        )
                    filter_exp = filter_exp.replace(complex_attr_exp, placeholder, 1)
                bracket_open_index = None
                complex_attr_rep = ""
            elif bracket_open_index is None:
                complex_attr_rep = ""

        if issues.can_proceed() and bracket_open_index is not None:
            issues.add_error(
                issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                proceed=False,
            )

        if not issues.can_proceed():
            for validated in placeholders.values():
                if hasattr(validated, "issues"):
                    issues.merge(issues=validated.issues)
            return issues

        issues.merge(Filter._validate_operator(filter_exp, placeholders))
        return issues

    @staticmethod
    def _validate_operator(exp: str, placeholders: Dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        bracket_open = False
        bracket_open_index = None
        bracket_cnt = 0
        op_exp_preprocessed = exp
        for i, char in enumerate(exp):
            if char == "(":
                if not bracket_open:
                    bracket_open = True
                    bracket_open_index = i
                bracket_cnt += 1
            elif char == ")":
                if bracket_open:
                    bracket_cnt -= 1
                else:
                    issues.add_error(
                        issue=ValidationError.bracket_not_opened_or_closed(), proceed=False
                    )
            if bracket_open and bracket_cnt == 0:
                group_op_exp = exp[bracket_open_index : i + 1]
                issues_ = Filter._validate_operator(
                    exp=group_op_exp[1:-1],  # without enclosing brackets
                    placeholders=placeholders,
                )
                id_, placeholder = get_placeholder()
                placeholders[id_] = _ValidatedGroupOperator(
                    issues=issues_,
                    expression=group_op_exp,
                )
                op_exp_preprocessed = op_exp_preprocessed.replace(group_op_exp, placeholder, 1)
                bracket_open = False
                bracket_open_index = None

        if bracket_open and bracket_open_index is not None:
            issues.add_error(issue=ValidationError.bracket_not_opened_or_closed(), proceed=False)

        op_exp_preprocessed = op_exp_preprocessed.strip()
        if op_exp_preprocessed == "":
            issues.add_error(issue=ValidationError.empty_filter_expression(), proceed=False)

        if not issues.can_proceed():
            return issues

        issues.merge(Filter._validate_op_or_exp(op_exp_preprocessed, placeholders))
        return issues

    @staticmethod
    def _validate_op_or_exp(exp: str, placeholders: Dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        or_operands, issues_ = Filter._validate_logical_operands(
            exp=exp,
            regexp=OR_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="or",
            placeholders=placeholders,
        )
        issues.merge(issues=issues_)
        if not or_operands:
            return issues
        for or_operand in or_operands:
            issues.merge(Filter._validate_op_and_exp(or_operand, placeholders))
        return issues

    @staticmethod
    def _validate_op_and_exp(exp: str, placeholders: Dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        and_operands, issues_ = Filter._validate_logical_operands(
            exp=exp,
            regexp=AND_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="and",
            placeholders=placeholders,
        )
        issues.merge(issues=issues_)
        if not and_operands:
            return issues

        for and_operand in and_operands:
            match = NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
            if match:
                not_operand = match.group(1)
                if not not_operand:
                    issues.add_error(
                        issue=ValidationError.missing_operand_for_operator(
                            operator="not",
                            expression=decode_placeholders(and_operand, placeholders),
                        ),
                        proceed=False,
                    )
                else:
                    issues.merge(Filter._validate_op_attr_exp(not_operand, placeholders))
            else:
                issues.merge(Filter._validate_op_attr_exp(and_operand, placeholders))
        return issues

    @staticmethod
    def _validate_logical_operands(
        exp: str,
        regexp: re.Pattern[str],
        operator_name: str,
        placeholders: Dict[str, Any],
    ) -> Tuple[List[str], ValidationIssues]:
        issues = ValidationIssues()
        operands = []
        current_position = 0
        matches = list(regexp.finditer(exp))
        for i, match in enumerate(matches):
            left_operand = exp[current_position : match.start()]
            if i == len(matches) - 1:
                right_operand = exp[match.end() :]
            else:
                right_operand = exp[match.end() : matches[i + 1].start()]

            invalid_exp = None
            if left_operand == right_operand == "":
                invalid_exp = match.group(0).strip()
            elif left_operand == "":
                deserialized_op = placeholders.get(deserialize_placeholder(right_operand))
                if deserialized_op is not None:
                    right_expression = deserialized_op.expression
                else:
                    right_expression = right_operand
                invalid_exp = (match.group(0) + right_expression).strip()
            elif right_operand == "":
                deserialized_op = placeholders.get(deserialize_placeholder(left_operand))
                if deserialized_op is not None:
                    left_expression = deserialized_op.expression
                else:
                    left_expression = left_operand
                invalid_exp = (left_expression + match.group(0)).strip()

            if invalid_exp is not None:
                issues.add_error(
                    issue=ValidationError.missing_operand_for_operator(
                        operator=operator_name,
                        expression=decode_placeholders(invalid_exp, placeholders),
                    ),
                    proceed=False,
                )

            if i == 0:
                operands.append(left_operand)
            operands.append(right_operand)
            current_position = match.end()

        if not matches:
            operands = [exp]

        operands = [operand for operand in operands if operand != ""]
        return operands, issues

    @staticmethod
    def _validate_op_attr_exp(attr_exp: str, placeholders: Dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        attr_exp = attr_exp.strip()
        sub_or_complex = placeholders.get(deserialize_placeholder(attr_exp))
        if sub_or_complex is not None:
            return sub_or_complex.issues

        components = OP_REGEX.split(attr_exp)
        if len(components) == 2:
            op_exp = components[1].lower()
            op_ = _UNARY_ATTR_OPERATORS.get(op_exp)
            if op_ is None:
                if op_exp in _BINARY_ATTR_OPERATORS:
                    issues.add_error(
                        issue=ValidationError.missing_operand_for_operator(
                            operator=op_exp,
                            expression=decode_placeholders(attr_exp, placeholders),
                        ),
                        proceed=False,
                    )
                else:
                    issues.add_error(
                        issue=ValidationError.unknown_operator(
                            operator_type="unary",
                            operator=decode_placeholders(components[1], placeholders),
                            expression=decode_placeholders(attr_exp, placeholders),
                        ),
                        proceed=False,
                    )
            attr_rep = decode_placeholders(components[0], placeholders)
            issues.merge(AttrRep.validate(attr_rep))
            return issues

        elif len(components) == 3:
            op_ = _BINARY_ATTR_OPERATORS.get(components[1].lower())
            if op_ is None:
                issues.add_error(
                    issue=ValidationError.unknown_operator(
                        operator_type="binary",
                        operator=decode_placeholders(components[1], placeholders),
                        expression=decode_placeholders(attr_exp, placeholders),
                    ),
                    proceed=False,
                )
            attr_rep = decode_placeholders(components[0], placeholders)
            issues.merge(AttrRep.validate(attr_rep))
            value = decode_placeholders(components[2], placeholders)
            try:
                value = deserialize_comparison_value(value)
            except ValueError:
                value = None
                issues.add_error(
                    issue=ValidationError.bad_comparison_value(
                        decode_placeholders(components[2], placeholders)
                    ),
                    proceed=False,
                )

            if not issues.can_proceed():
                return issues

            if type(value) not in _ALLOWED_VALUE_TYPES_FOR_BINARY_OPERATORS[op_]:
                issues.add_error(
                    issue=ValidationError.non_compatible_comparison_value(value, op_.SCIM_OP),
                    proceed=False,
                )

            if not issues.can_proceed():
                return issues

            return issues

        issues.add_error(
            issue=ValidationError.unknown_expression(decode_placeholders(attr_exp, placeholders)),
            proceed=False,
        )
        return issues

    @classmethod
    def deserialize(cls, filter_exp: str) -> "Filter":
        try:
            return cls._deserialize(filter_exp)
        except Exception:
            raise ValueError("invalid filter expression")

    @classmethod
    def _deserialize(cls, filter_exp: str) -> "Filter":
        filter_exp, placeholders = encode_strings(filter_exp)
        for match in COMPLEX_OPERATOR_REGEX.finditer(filter_exp):
            complex_attr_rep = match.group(1)
            attr_rep = AttrRep.deserialize(complex_attr_rep)
            assert not attr_rep.sub_attr
            sub_op_exp = match.group(2)
            deserialized_sub_op = Filter._deserialize_operator(sub_op_exp, placeholders)
            id_, placeholder = get_placeholder()
            placeholders[id_] = op.ComplexAttributeOperator(
                attr_rep=attr_rep,
                sub_operator=deserialized_sub_op,
            )
            filter_exp = filter_exp.replace(match.group(0), placeholder, 1)

        deserialized_op = Filter._deserialize_operator(filter_exp, placeholders)
        return cls(deserialized_op)

    @staticmethod
    def _deserialize_operator(exp: str, placeholders: Dict[str, Any]) -> _DeserializedOperator:
        for match in GROUP_OPERATOR_REGEX.finditer(exp):
            sub_op_exp = match.group(0)
            deserialized_op = Filter._deserialize_operator(
                exp=sub_op_exp[1:-1],  # without enclosing brackets
                placeholders=placeholders,
            )
            id_, placeholder = get_placeholder()
            placeholders[id_] = deserialized_op
            exp = exp.replace(sub_op_exp, placeholder, 1)
        return Filter._deserialize_op_or_exp(exp, placeholders)

    @staticmethod
    def _deserialize_op_or_exp(exp: str, placeholders: Dict[str, Any]) -> _DeserializedOperator:
        or_operands = Filter._split_exp_to_logical_operands(
            exp=exp,
            regexp=OR_LOGICAL_OPERATOR_SPLIT_REGEX,
        )
        deserialized_or_operands = []
        for or_operand in or_operands:
            deserialized_or_operands.append(
                Filter._deserialize_op_and_exp(or_operand, placeholders)
            )
        if len(deserialized_or_operands) == 1:
            return deserialized_or_operands[0]
        return op.Or(*deserialized_or_operands)

    @staticmethod
    def _deserialize_op_and_exp(exp: str, placeholders: Dict[str, Any]) -> _DeserializedOperator:
        and_operands = Filter._split_exp_to_logical_operands(
            exp=exp,
            regexp=AND_LOGICAL_OPERATOR_SPLIT_REGEX,
        )
        deserialized_and_operands = []
        for and_operand in and_operands:
            match = NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
            if match:
                deserialized_and_operand = op.Not(
                    Filter._deserialize_op_attr_exp(match.group(1), placeholders)
                )
            else:
                deserialized_and_operand = Filter._deserialize_op_attr_exp(
                    and_operand, placeholders
                )
            deserialized_and_operands.append(deserialized_and_operand)
        if len(deserialized_and_operands) == 1:
            return deserialized_and_operands[0]
        return op.And(*deserialized_and_operands)

    @staticmethod
    def _split_exp_to_logical_operands(exp: str, regexp: re.Pattern[str]) -> List[str]:
        operands = []
        current_position = 0
        matches = list(regexp.finditer(exp))
        for i, match in enumerate(matches):
            left_operand = exp[current_position : match.start()]
            if i == 0:
                operands.append(left_operand)

            if i == len(matches) - 1:
                right_operand = exp[match.end() :]
            else:
                right_operand = exp[match.end() : matches[i + 1].start()]
            operands.append(right_operand)
            current_position = match.end()
        if not matches:
            operands = [exp]

        assert "" not in operands
        return operands

    @staticmethod
    def _deserialize_op_attr_exp(exp: str, placeholders: Dict[str, Any]) -> _DeserializedOperator:
        exp = exp.strip()
        sub_or_complex = placeholders.get(deserialize_placeholder(exp))
        if sub_or_complex is not None:
            return sub_or_complex
        components = OP_REGEX.split(exp)
        assert len(components) in [2, 3]

        if len(components) == 2:
            op_exp = components[1].lower()
            op_ = _UNARY_ATTR_OPERATORS[op_exp]
            attr_rep = AttrRep.deserialize(components[0])
            if attr_rep.sub_attr:
                return op.ComplexAttributeOperator(
                    attr_rep=AttrRep(schema=attr_rep.schema, attr=attr_rep.attr),
                    sub_operator=op_(AttrRep(attr=attr_rep.sub_attr)),
                )
            return op_(attr_rep)
        op_ = _BINARY_ATTR_OPERATORS.get(components[1].lower())
        attr_rep = AttrRep.deserialize(components[0])
        value = deserialize_comparison_value(decode_placeholders(components[2], placeholders))
        if attr_rep.sub_attr:
            return op.ComplexAttributeOperator(
                attr_rep=AttrRep(schema=attr_rep.schema, attr=attr_rep.attr),
                sub_operator=op_(AttrRep(attr=attr_rep.sub_attr), value),
            )
        return op_(attr_rep, value)

    def __call__(
        self, data: SCIMDataContainer, schema: "BaseSchema", strict: bool = True
    ) -> op.MatchResult:
        if not isinstance(self._operator, op.LogicalOperator):
            data = data.get(self._operator.attr_rep)
        return self._operator.match(data, schema.attrs, strict)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Filter):
            return False
        return SCIMDataContainer(self.to_dict()) == SCIMDataContainer(other.to_dict())

    def to_dict(self):
        return self._to_dict(self._operator)

    @staticmethod
    def _to_dict(operator):
        if isinstance(operator, op.AttributeOperator):
            filter_dict = {
                "op": operator.SCIM_OP,
                "attr_rep": operator.attr_rep.sub_attr or operator.attr_rep.attr_with_schema,
            }
            if isinstance(operator, op.BinaryAttributeOperator):
                filter_dict["value"] = operator.value
            return filter_dict

        if isinstance(operator, op.ComplexAttributeOperator):
            return {
                "op": "complex",
                "attr_rep": operator.attr_rep.sub_attr or operator.attr_rep.attr_with_schema,
                "sub_op": Filter._to_dict(operator.sub_operator),
            }

        if isinstance(operator, op.Not):
            return {
                "op": operator.SCIM_OP,
                "sub_op": Filter._to_dict(operator.sub_operator),
            }

        if isinstance(operator, op.MultiOperandLogicalOperator):
            return {
                "op": operator.SCIM_OP,
                "sub_ops": [
                    Filter._to_dict(sub_operator) for sub_operator in operator.sub_operators
                ],
            }
        raise TypeError(f"unsupported filter type '{type(operator).__name__}'")
