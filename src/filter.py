import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, TypeAlias, Union

from src.data import operator as op
from src.data.container import AttrRep, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.utils import (
    OP_REGEX,
    PLACEHOLDER_REGEX,
    STRING_VALUES_REGEX,
    get_placeholder,
    parse_comparison_value,
    parse_placeholder,
)

if TYPE_CHECKING:
    from src.schemas import BaseSchema

OR_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\bor\b\s*", flags=re.DOTALL)
AND_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\band\b\s*", flags=re.DOTALL)
NOT_LOGICAL_OPERATOR_REGEX = re.compile(r"\s*\bnot\b\s*(.*)", flags=re.DOTALL)

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


_ParsedOperator: TypeAlias = Union[
    op.AttributeOperator,
    op.LogicalOperator,
    op.ComplexAttributeOperator,
]


@dataclass
class _ParsedComplexAttributeOperator:
    operator: Optional[op.ComplexAttributeOperator]
    issues: ValidationIssues
    expression: str


@dataclass
class _ParsedGroupOperator:
    operator: Optional[Union[op.AttributeOperator, op.LogicalOperator]]
    issues: ValidationIssues
    expression: str


class Filter:
    def __init__(self, operator: _ParsedOperator):
        self._operator = operator

    @property
    def operator(self) -> _ParsedOperator:
        return self._operator

    @classmethod
    def parse(cls, filter_exp: str) -> Tuple[Optional["Filter"], ValidationIssues]:
        issues = ValidationIssues()

        string_values = {}
        for match in STRING_VALUES_REGEX.finditer(filter_exp):
            start, stop = match.span()
            string_value = match.string[start:stop]
            string_values[start] = string_value
            filter_exp = filter_exp.replace(string_value, get_placeholder(start), 1)

        bracket_open_index = None
        complex_attr_rep = ""
        parsed_complex_ops = {}
        filter_exp_iter_copy = filter_exp
        ignore_processing = False
        issues_ = ValidationIssues()
        for i, char in enumerate(filter_exp_iter_copy):
            if char == '"':
                ignore_processing = not ignore_processing
            if ignore_processing:
                continue

            if (re.match(r"\w", char) or char in ":.") and bracket_open_index is None:
                complex_attr_rep += char
            elif char == "[":
                if bracket_open_index is not None:
                    issues.add(
                        issue=ValidationError.inner_complex_attribute_or_square_bracket(),
                        proceed=False,
                    )
                    break
                else:
                    bracket_open_index = i
            elif char == "]":
                if bracket_open_index is None:
                    issues.add(
                        issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                        proceed=False,
                    )
                else:
                    sub_ops_exp = filter_exp_iter_copy[bracket_open_index + 1 : i]
                    complex_attr_start = bracket_open_index - len(complex_attr_rep)
                    complex_attr_exp = f"{complex_attr_rep}[{sub_ops_exp}]"
                    if sub_ops_exp.strip() == "":
                        issues_.add(
                            issue=ValidationError.empty_complex_attribute_expression(
                                complex_attr_rep
                            ),
                            proceed=False,
                        )
                    attr_rep = AttrRep.parse(complex_attr_rep)
                    if attr_rep is None:
                        issues_.add(
                            issue=ValidationError.bad_attribute_name(complex_attr_rep),
                            proceed=False,
                        )
                    elif attr_rep.sub_attr:
                        issues_.add(
                            issue=ValidationError.complex_sub_attribute(
                                attr=attr_rep.attr, sub_attr=attr_rep.sub_attr
                            ),
                            proceed=False,
                        )
                    if not issues_.can_proceed():
                        parsed_complex_ops[complex_attr_start] = _ParsedComplexAttributeOperator(
                            operator=None,
                            issues=issues_,
                            expression=complex_attr_exp,
                        )
                    else:
                        parsed_complex_sub_ops, issues_ = Filter._parse_operator(
                            op_exp=sub_ops_exp,
                            string_values=string_values,
                        )
                        if not issues_.can_proceed():
                            operator = None
                        else:
                            operator = op.ComplexAttributeOperator(
                                attr_rep=attr_rep,
                                sub_operator=parsed_complex_sub_ops,
                            )
                        parsed_complex_ops[complex_attr_start] = _ParsedComplexAttributeOperator(
                            operator=operator,
                            issues=issues_,
                            expression=complex_attr_exp,
                        )
                    filter_exp = filter_exp.replace(
                        complex_attr_exp, get_placeholder(complex_attr_start), 1
                    )
                bracket_open_index = None
                complex_attr_rep = ""
                issues_ = ValidationIssues()
            elif bracket_open_index is None:
                complex_attr_rep = ""
                issues_ = ValidationIssues()

        if not issues.can_proceed():
            for parsed in parsed_complex_ops.values():
                issues.merge(issues=parsed.issues)
            return None, issues

        if bracket_open_index and bracket_open_index not in parsed_complex_ops:
            issues.add(
                issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                proceed=False,
            )

        if not issues.can_proceed():
            for parsed in parsed_complex_ops.values():
                issues.merge(issues=parsed.issues)
            return None, issues

        parsed_op, issues_ = Filter._parse_operator(
            op_exp=filter_exp,
            string_values=string_values,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            return None, issues
        return cls(parsed_op), issues

    @staticmethod
    def _parse_operator(
        op_exp: str,
        string_values: Dict[int, str],
        parsed_complex_ops: Optional[Dict[int, _ParsedComplexAttributeOperator]] = None,
    ) -> Tuple[Optional[_ParsedOperator], ValidationIssues]:
        parsed_complex_ops = parsed_complex_ops or {}
        issues = ValidationIssues()
        ignore_processing = False
        bracket_open = False
        bracket_open_index = None
        bracket_cnt = 0
        parsed_group_ops = {}
        op_exp_preprocessed = op_exp
        for i, char in enumerate(op_exp):
            if char == '"':
                ignore_processing = not ignore_processing
            if ignore_processing:
                continue

            if char == "(":
                if not bracket_open:
                    bracket_open = True
                    bracket_open_index = i
                bracket_cnt += 1
            elif char == ")":
                if bracket_open:
                    bracket_cnt -= 1
                else:
                    issues.add(issue=ValidationError.bracket_not_opened_or_closed(), proceed=False)
            if bracket_open and bracket_cnt == 0:
                group_op_exp = op_exp[bracket_open_index : i + 1]
                parsed_group_op, issues_ = Filter._parse_operator(
                    op_exp=group_op_exp[1:-1],  # without enclosing brackets
                    string_values=string_values,
                    parsed_complex_ops=parsed_complex_ops,
                )
                parsed_group_ops[bracket_open_index] = _ParsedGroupOperator(
                    operator=parsed_group_op,
                    issues=issues_,
                    expression=group_op_exp,
                )
                op_exp_preprocessed = op_exp_preprocessed.replace(
                    group_op_exp, get_placeholder(bracket_open_index), 1
                )
                bracket_open = False
                bracket_open_index = None

        if bracket_open and bracket_open_index not in parsed_group_ops:
            issues.add(issue=ValidationError.bracket_not_opened_or_closed(), proceed=False)

        op_exp_preprocessed = op_exp_preprocessed.strip()
        if op_exp_preprocessed == "":
            issues.add(issue=ValidationError.empty_filter_expression(), proceed=False)

        if not issues.can_proceed():
            return None, issues

        parsed_op, issues_ = Filter._parsed_op_or_exp(
            or_exp=op_exp_preprocessed,
            string_values=string_values,
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            return None, issues
        return parsed_op, issues

    @staticmethod
    def _parsed_op_or_exp(
        or_exp: str,
        string_values: Dict[int, str],
        parsed_group_ops: Dict[int, _ParsedGroupOperator],
        parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
    ) -> Tuple[Optional[_ParsedOperator], ValidationIssues]:
        issues = ValidationIssues()
        or_operands, issues_ = Filter._split_exp_to_logical_operands(
            op_exp=or_exp,
            regexp=OR_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="or",
            string_values=string_values,
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not or_operands:
            return None, issues

        parsed_or_operands = []
        for or_operand in or_operands:
            parsed_or_operand, issues_ = Filter._parse_op_and_exp(
                and_exp=or_operand,
                string_values=string_values,
                parsed_group_ops=parsed_group_ops,
                parsed_complex_ops=parsed_complex_ops,
            )
            issues.merge(issues=issues_)
            if not issues.can_proceed():
                parsed_or_operand = None
            parsed_or_operands.append(parsed_or_operand)

        if not issues.can_proceed():
            return None, issues

        if len(parsed_or_operands) == 1:
            return parsed_or_operands[0], issues
        return op.Or(*parsed_or_operands), issues

    @staticmethod
    def _parse_op_and_exp(
        and_exp: str,
        string_values: Dict[int, str],
        parsed_group_ops: Dict[int, _ParsedGroupOperator],
        parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
    ) -> Tuple[Optional[_ParsedOperator], ValidationIssues]:
        issues = ValidationIssues()
        and_operands, issues_ = Filter._split_exp_to_logical_operands(
            op_exp=and_exp,
            regexp=AND_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="and",
            string_values=string_values,
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not and_operands:
            return None, issues

        parsed_and_operands = []
        for and_operand in and_operands:
            match = NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
            if match:
                not_operand = match.group(1)
                if not not_operand:
                    issues.add(
                        issue=ValidationError.missing_operand_for_operator(
                            operator="not",
                            expression=Filter._encode_placeholders(
                                exp=and_operand,
                                string_values=string_values,
                            ),
                        ),
                        proceed=False,
                    )
                    parsed_and_operand = None
                else:
                    parsed_and_operand, issues_ = Filter._parse_op_attr_exp(
                        attr_exp=not_operand,
                        string_values=string_values,
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    )
                    issues.merge(issues=issues_)
                    if not issues.can_proceed():
                        parsed_and_operand = None
                    else:
                        parsed_and_operand = op.Not(parsed_and_operand)
            else:
                parsed_and_operand, issues_ = Filter._parse_op_attr_exp(
                    attr_exp=and_operand,
                    string_values=string_values,
                    parsed_group_ops=parsed_group_ops,
                    parsed_complex_ops=parsed_complex_ops,
                )
                issues.merge(issues=issues_)
                if not issues.can_proceed():
                    parsed_and_operand = None
            parsed_and_operands.append(parsed_and_operand)

        if not issues.can_proceed():
            return None, issues

        if len(parsed_and_operands) == 1:
            return parsed_and_operands[0], issues
        return op.And(*parsed_and_operands), issues

    @staticmethod
    def _split_exp_to_logical_operands(
        op_exp: str,
        regexp: re.Pattern[str],
        operator_name: str,
        string_values: Dict[int, str],
        parsed_group_ops: Dict[int, _ParsedGroupOperator],
        parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
    ) -> Tuple[List[str], ValidationIssues]:
        issues = ValidationIssues()
        operands = []
        current_position = 0
        matches = list(regexp.finditer(op_exp))
        for i, match in enumerate(matches):
            left_operand = op_exp[current_position : match.start()]
            if i == len(matches) - 1:
                right_operand = op_exp[match.end() :]
            else:
                right_operand = op_exp[match.end() : matches[i + 1].start()]

            invalid_expression = None
            if left_operand == right_operand == "":
                invalid_expression = match.group(0).strip()
            elif left_operand == "":
                parsed_op = Filter._get_parsed_group_or_complex_op(
                    op_exp=right_operand,
                    parsed_group_ops=parsed_group_ops,
                    parsed_complex_ops=parsed_complex_ops,
                )
                if parsed_op is not None:
                    right_expression = parsed_op.expression
                else:
                    right_expression = right_operand
                invalid_expression = (match.group(0) + right_expression).strip()
            elif right_operand == "":
                parsed_op = Filter._get_parsed_group_or_complex_op(
                    op_exp=left_operand,
                    parsed_group_ops=parsed_group_ops,
                    parsed_complex_ops=parsed_complex_ops,
                )
                if parsed_op is not None:
                    left_expression = parsed_op.expression
                else:
                    left_expression = left_operand
                invalid_expression = (left_expression + match.group(0)).strip()

            if invalid_expression is not None:
                issues.add(
                    issue=ValidationError.missing_operand_for_operator(
                        operator=operator_name,
                        expression=Filter._encode_placeholders(
                            exp=invalid_expression,
                            string_values=string_values,
                        ),
                    ),
                    proceed=False,
                )

            if i == 0:
                operands.append(left_operand)
            operands.append(right_operand)
            current_position = match.end()

        if not matches:
            operands = [op_exp]

        operands = [operand for operand in operands if operand != ""]
        return operands, issues

    @staticmethod
    def _parse_op_attr_exp(
        attr_exp: str,
        string_values: Dict[int, str],
        parsed_group_ops: Dict[int, _ParsedGroupOperator],
        parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
    ) -> Tuple[Optional[_ParsedOperator], ValidationIssues]:
        issues = ValidationIssues()
        attr_exp = attr_exp.strip()
        sub_or_complex = Filter._get_parsed_group_or_complex_op(
            op_exp=attr_exp,
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        if sub_or_complex is not None:
            return sub_or_complex.operator, sub_or_complex.issues

        components = OP_REGEX.split(attr_exp)
        if len(components) == 2:
            op_exp = components[1].lower()
            op_ = _UNARY_ATTR_OPERATORS.get(op_exp)
            if op_ is None:
                if op_exp in _BINARY_ATTR_OPERATORS:
                    issues.add(
                        issue=ValidationError.missing_operand_for_operator(
                            operator=op_exp,
                            expression=Filter._encode_placeholders(
                                exp=attr_exp,
                                string_values=string_values,
                                parsed_group_ops=parsed_group_ops,
                                parsed_complex_ops=parsed_complex_ops,
                            ),
                        ),
                        proceed=False,
                    )
                else:
                    issues.add(
                        issue=ValidationError.unknown_operator(
                            operator_type="unary",
                            operator=Filter._encode_placeholders(
                                exp=components[1],
                                string_values=string_values,
                                parsed_group_ops=parsed_group_ops,
                                parsed_complex_ops=parsed_complex_ops,
                            ),
                            expression=Filter._encode_placeholders(
                                exp=attr_exp,
                                string_values=string_values,
                                parsed_group_ops=parsed_group_ops,
                                parsed_complex_ops=parsed_complex_ops,
                            ),
                        ),
                        proceed=False,
                    )
            attr_rep = AttrRep.parse(components[0])
            if attr_rep is None:
                issues.add(
                    issue=ValidationError.bad_attribute_name(
                        Filter._encode_placeholders(
                            exp=components[0],
                            string_values=string_values,
                            parsed_group_ops=parsed_group_ops,
                            parsed_complex_ops=parsed_complex_ops,
                        )
                    ),
                    proceed=False,
                )
            if not issues.can_proceed():
                return None, issues

            if attr_rep.sub_attr:
                operator = op.ComplexAttributeOperator(
                    attr_rep=AttrRep(schema=attr_rep.schema, attr=attr_rep.attr),
                    sub_operator=op_(AttrRep(attr=attr_rep.sub_attr)),
                )
            else:
                operator = op_(attr_rep)
            return operator, issues

        elif len(components) == 3:
            op_ = _BINARY_ATTR_OPERATORS.get(components[1].lower())
            if op_ is None:
                issues.add(
                    issue=ValidationError.unknown_operator(
                        operator_type="binary",
                        operator=Filter._encode_placeholders(
                            exp=components[1],
                            string_values=string_values,
                            parsed_group_ops=parsed_group_ops,
                            parsed_complex_ops=parsed_complex_ops,
                        ),
                        expression=Filter._encode_placeholders(
                            exp=attr_exp,
                            string_values=string_values,
                            parsed_group_ops=parsed_group_ops,
                            parsed_complex_ops=parsed_complex_ops,
                        ),
                    ),
                    proceed=False,
                )
            attr_rep = AttrRep.parse(components[0])
            if attr_rep is None:
                issues.add(
                    issue=ValidationError.bad_attribute_name(
                        Filter._encode_placeholders(
                            exp=components[0],
                            string_values=string_values,
                            parsed_group_ops=parsed_group_ops,
                            parsed_complex_ops=parsed_complex_ops,
                        )
                    ),
                    proceed=False,
                )

            value = Filter._encode_placeholders(
                exp=components[2],
                string_values=string_values,
            )

            try:
                value = parse_comparison_value(value)
            except ValueError:
                value = None
                issues.add(
                    issue=ValidationError.bad_comparison_value(
                        Filter._encode_placeholders(
                            exp=components[2],
                            string_values=string_values,
                            parsed_group_ops=parsed_group_ops,
                            parsed_complex_ops=parsed_complex_ops,
                        )
                    ),
                    proceed=False,
                )

            if not issues.can_proceed():
                return None, issues

            if type(value) not in _ALLOWED_VALUE_TYPES_FOR_BINARY_OPERATORS[op_]:
                issues.add(
                    issue=ValidationError.non_compatible_comparison_value(value, op_.SCIM_OP),
                    proceed=False,
                )

            if not issues.can_proceed():
                return None, issues

            if attr_rep.sub_attr:
                operator = op.ComplexAttributeOperator(
                    attr_rep=AttrRep(schema=attr_rep.schema, attr=attr_rep.attr),
                    sub_operator=op_(AttrRep(attr=attr_rep.sub_attr), value),
                )
            else:
                operator = op_(attr_rep, value)
            return operator, issues

        issues.add(
            issue=ValidationError.unknown_expression(
                Filter._encode_placeholders(
                    exp=attr_exp,
                    string_values=string_values,
                    parsed_group_ops=parsed_group_ops,
                    parsed_complex_ops=parsed_complex_ops,
                )
            ),
            proceed=False,
        )
        return None, issues

    @staticmethod
    def _get_parsed_group_or_complex_op(
        op_exp: str,
        parsed_group_ops: Dict[int, _ParsedGroupOperator],
        parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
    ) -> Optional[Union[_ParsedGroupOperator, _ParsedComplexAttributeOperator]]:
        position = parse_placeholder(op_exp)
        if position is None:
            return None
        if position in parsed_group_ops:
            return parsed_group_ops[position]
        elif position in parsed_complex_ops:
            return parsed_complex_ops[position]
        return None

    @staticmethod
    def _encode_placeholders(
        exp: str,
        string_values: Optional[Dict[int, str]] = None,
        parsed_group_ops: Optional[Dict[int, _ParsedGroupOperator]] = None,
        parsed_complex_ops: Optional[Dict[int, _ParsedComplexAttributeOperator]] = None,
    ):
        encoded = exp
        for match in PLACEHOLDER_REGEX.finditer(exp):
            index = int(match.group(1))
            if index in (string_values or {}):
                encoded = encoded.replace(match.group(0), string_values[index])
            elif index in (parsed_group_ops or {}):
                encoded = encoded.replace(match.group(0), parsed_group_ops[index].expression)
            elif index in (parsed_complex_ops or {}):
                encoded = encoded.replace(match.group(0), parsed_complex_ops[index].expression)

        return encoded

    def __call__(
        self, data: SCIMDataContainer, schema: "BaseSchema", strict: bool = True
    ) -> op.MatchResult:
        if not isinstance(self._operator, op.LogicalOperator):
            data = data[self._operator.attr_rep]
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
