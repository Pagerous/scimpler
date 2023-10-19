import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from src.parser.attributes.attributes import ComplexAttribute
from src.parser.error import ValidationError, ValidationIssues
from src.parser.parameters.filter import operator as op
from src.parser.resource.schemas import Schema

_ATTR_NAME_REGEX = re.compile(r"\w+")
_SUB_ATTR_NAME_REGEX = re.compile(r"\w+\.\w+")
_URI_ATTR_PREFIX = rf"(?:[\w.-]+:)*"

_ALLOWED_IDENTIFIERS = re.compile(
    rf"({_URI_ATTR_PREFIX})?({_ATTR_NAME_REGEX.pattern}|{_SUB_ATTR_NAME_REGEX.pattern})"
)

_OR_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\bor\b\s*", flags=re.DOTALL)
_AND_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\band\b\s*", flags=re.DOTALL)
_NOT_LOGICAL_OPERATOR_REGEX = re.compile(r"\s*\bnot\b\s+(.*)", flags=re.DOTALL)

_PLACEHOLDER_REGEX = re.compile(r"\|&PLACE_HOLDER_(\d+)&\|")

_LOGICAL_OPERATORS = {
    "and": op.And,
    "or": op.Or,
    "not": op.Not,
}

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

_AllowedOperandValues = Union[str, bool, int, float, None]

ParsedOperator = Union[
    op.AttributeOperator,
    op.LogicalOperator,
    op.ComplexAttributeOperator,
]


class Filter:
    def __init__(self, operator: ParsedOperator):
        self._operator = operator

    def match(self, data: Dict[str, Any], schema: Optional[Schema]) -> bool:
        if isinstance(self._operator, op.AttributeOperator):
            if schema is not None:
                attr = schema.attributes.get(self._operator.attr_name)
                if attr is None:
                    return False
            else:
                attr = None
            return self._operator.match(data.get(self._operator.attr_name), attr)
        if isinstance(self._operator, op.ComplexAttributeOperator):
            if schema is not None:
                attr = schema.attributes.get(self._operator.attr_name)
                if not isinstance(attr, ComplexAttribute):
                    return False
            else:
                attr = None
            return self._operator.match(data.get(self._operator.attr_name), attr)
        if isinstance(self._operator, op.LogicalOperator):
            if schema is not None:
                attrs = schema.attributes
            else:
                attrs = None
            return self._operator.match(data, attrs)
        return False

    def to_dict(self):
        return self._to_dict(self._operator)

    @staticmethod
    def _to_dict(operator):
        if isinstance(operator, op.AttributeOperator):
            filter_dict = {
                "op": operator.SCIM_OP,
                "attr_name": operator.display_name,
            }
            if isinstance(operator, op.BinaryAttributeOperator):
                filter_dict["value"] = operator.value
            return filter_dict

        if isinstance(operator, op.ComplexAttributeOperator):
            return {
                "op": "complex",
                "attr_name": operator.display_name,
                "sub_op": Filter._to_dict(operator.sub_operator)
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
                ]
            }
        raise TypeError(f"unsupported filter type '{type(operator).__name__}'")


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


def parse_filter(filter_exp: str) -> Tuple[Optional[Filter], ValidationIssues]:
    issues = ValidationIssues()
    bracket_open_index = None
    complex_attr_name = ""
    parsed_complex_ops = {}
    filter_exp_preprocessed = filter_exp
    ignore_processing = False
    issues_ = ValidationIssues()
    for i, char in enumerate(filter_exp_preprocessed):
        if char == "\"":
            ignore_processing = not ignore_processing
        if ignore_processing:
            continue

        if (re.match(r"\w", char) or char in ":.") and bracket_open_index is None:
            complex_attr_name += char
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
                    issue=ValidationError.no_opening_complex_attribute_bracket(i),
                    proceed=False,
                )
            else:
                sub_ops_exp = filter_exp_preprocessed[bracket_open_index+1:i]
                complex_attr_start = bracket_open_index - len(complex_attr_name)
                complex_attr_exp = f"{complex_attr_name}[{sub_ops_exp}]"
                if sub_ops_exp.strip() == "":
                    issues_.add(
                        issue=ValidationError.empty_complex_attribute_expression(
                            complex_attr_name, complex_attr_start
                        ),
                        proceed=False,
                    )
                if complex_attr_name == "":
                    issues_.add(
                        issue=ValidationError.complex_attribute_without_top_level_attribute(
                            complex_attr_exp
                        ),
                        proceed=False,
                    )
                elif not _ALLOWED_IDENTIFIERS.fullmatch(complex_attr_name):
                    issues_.add(
                        issue=ValidationError.bad_attribute_name(complex_attr_name),
                        proceed=False,
                    )
                if not issues_.can_proceed():
                    parsed_complex_ops[complex_attr_start] = _ParsedComplexAttributeOperator(
                        operator=None,
                        issues=issues_,
                        expression=complex_attr_exp,
                    )
                else:
                    parsed_complex_sub_ops, issues_ = _parse_operator(
                        op_exp=sub_ops_exp,
                    )
                    if not issues_.can_proceed():
                        operator = None
                    else:
                        operator = op.ComplexAttributeOperator(
                            complex_attr_name, parsed_complex_sub_ops
                        )
                    parsed_complex_ops[complex_attr_start] = _ParsedComplexAttributeOperator(
                        operator=operator,
                        issues=issues_,
                        expression=complex_attr_exp,
                    )
                filter_exp = filter_exp.replace(
                    complex_attr_exp, _get_placeholder(complex_attr_start), 1
                )
            bracket_open_index = None
            complex_attr_name = ""
            issues_ = ValidationIssues()
        elif bracket_open_index is None:
            complex_attr_name = ""
            issues_ = ValidationIssues()

    if not issues.can_proceed():
        for parsed in parsed_complex_ops.values():
            issues.merge(issues=parsed.issues)
        return None, issues

    if bracket_open_index and bracket_open_index not in parsed_complex_ops:
        issues.add(
            issue=ValidationError.no_closing_complex_attribute_bracket(bracket_open_index),
            proceed=False,
        )

    if not issues.can_proceed():
        for parsed in parsed_complex_ops.values():
            issues.merge(issues=parsed.issues)
        return None, issues

    parsed_op, issues_ = _parse_operator(
        op_exp=filter_exp,
        parsed_complex_ops=parsed_complex_ops,
    )
    issues.merge(issues=issues_)
    if not issues.can_proceed():
        return None, issues
    return Filter(parsed_op), issues


def _parse_operator(
    op_exp: str,
    parsed_complex_ops: Optional[Dict[int, _ParsedComplexAttributeOperator]] = None,
) -> Tuple[Optional[ParsedOperator], ValidationIssues]:
    parsed_complex_ops = parsed_complex_ops or {}
    issues = ValidationIssues()
    ignore_processing = False
    bracket_open = False
    bracket_open_index = None
    bracket_cnt = 0
    parsed_group_ops = {}
    op_exp_preprocessed = op_exp
    for i, char in enumerate(op_exp):
        if char == "\"":
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
                issues.add(issue=ValidationError.no_opening_bracket(i), proceed=False)
        if bracket_open and bracket_cnt == 0:
            group_op_exp = op_exp[bracket_open_index:i + 1]
            parsed_group_op, issues_ = _parse_operator(
                op_exp=group_op_exp[1:-1],  # without enclosing brackets
                parsed_complex_ops=parsed_complex_ops,
            )
            parsed_group_ops[bracket_open_index] = _ParsedGroupOperator(
                operator=parsed_group_op,
                issues=issues_,
                expression=group_op_exp,
            )
            op_exp_preprocessed = op_exp_preprocessed.replace(
                group_op_exp, _get_placeholder(bracket_open_index), 1
            )
            bracket_open = False
            bracket_open_index = None

    if bracket_open and bracket_open_index not in parsed_group_ops:
        issues.add(issue=ValidationError.no_closing_bracket(bracket_open_index), proceed=False)

    op_exp_preprocessed = op_exp_preprocessed.strip()
    if op_exp_preprocessed == "":
        issues.add(issue=ValidationError.empty_expression(), proceed=False)

    if not issues.can_proceed():
        return None, issues

    parsed_op, issues_ = _parsed_op_or_exp(
        or_exp=op_exp_preprocessed,
        parsed_group_ops=parsed_group_ops,
        parsed_complex_ops=parsed_complex_ops,
    )
    issues.merge(issues=issues_)
    if not issues.can_proceed():
        return None, issues
    return parsed_op, issues


def _parsed_op_or_exp(
    or_exp: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
) -> Tuple[Optional[ParsedOperator], ValidationIssues]:
    issues = ValidationIssues()
    or_operands, issues_ = _split_exp_to_logical_operands(
        op_exp=or_exp,
        regexp=_OR_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="or",
        parsed_group_ops=parsed_group_ops,
        parsed_complex_ops=parsed_complex_ops,
    )
    issues.merge(issues=issues_)
    if not or_operands:
        return None, issues

    if len(or_operands) == 1:
        parsed_or_operand, issues_ = _parse_op_and_exp(
            and_exp=or_operands[0],
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_or_operand = None
        return parsed_or_operand, issues

    parsed_or_operands = []
    for or_operand in or_operands:
        parsed_or_operand, issues_ = _parse_op_and_exp(
            and_exp=or_operand,
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_or_operand = None
        parsed_or_operands.append(parsed_or_operand)

    if not issues.can_proceed():
        return None, issues
    return op.Or(*parsed_or_operands), issues


def _parse_op_and_exp(
    and_exp: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
) -> Tuple[Optional[ParsedOperator], ValidationIssues]:
    issues = ValidationIssues()
    and_operands, issues_ = _split_exp_to_logical_operands(
        op_exp=and_exp,
        regexp=_AND_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="and",
        parsed_group_ops=parsed_group_ops,
        parsed_complex_ops=parsed_complex_ops,
    )
    issues.merge(issues=issues_)
    if not and_operands:
        return None, issues

    if len(and_operands) == 1:
        parsed_and_operand, issues_ = _parse_op_attr_exp(
            attr_exp=and_operands[0],
            parsed_group_ops=parsed_group_ops,
            parsed_complex_ops=parsed_complex_ops,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_and_operand = None
        return parsed_and_operand, issues

    parsed_and_operands = []
    for and_operand in and_operands:
        match = _NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
        if match:
            parsed_and_operand, issues_ = _parse_op_attr_exp(
                attr_exp=match.group(1),
                parsed_group_ops=parsed_group_ops,
                parsed_complex_ops=parsed_complex_ops,
            )
            issues.merge(issues=issues_)
            if not issues.can_proceed():
                parsed_and_operand = None
            else:
                parsed_and_operand = op.Not(parsed_and_operand)
        else:
            parsed_and_operand, issues_ = _parse_op_attr_exp(
                attr_exp=and_operand,
                parsed_group_ops=parsed_group_ops,
                parsed_complex_ops=parsed_complex_ops,
            )
            issues.merge(issues=issues_)
            if not issues.can_proceed():
                parsed_and_operand = None
        parsed_and_operands.append(parsed_and_operand)

    if not issues.can_proceed():
        return None, issues
    return op.And(*parsed_and_operands), issues


def _split_exp_to_logical_operands(
    op_exp: str,
    regexp: re.Pattern[str],
    operator_name: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
) -> Tuple[List[str], ValidationIssues]:
    issues = ValidationIssues()
    operands = []
    current_position = 0
    matches = list(regexp.finditer(op_exp))
    for i, match in enumerate(matches):
        left_operand = op_exp[current_position:match.start()]
        if i == len(matches) - 1:
            right_operand = op_exp[match.end():]
        else:
            right_operand = op_exp[match.end():matches[i + 1].start()]

        invalid_expression = None
        if left_operand == right_operand == "":
            invalid_expression = match.group(0).strip()
        elif left_operand == "":
            parsed_op = _get_parsed_group_or_complex_op(
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
            parsed_op = _get_parsed_group_or_complex_op(
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
                    expression=invalid_expression,
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


def _parse_op_attr_exp(
    attr_exp: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
) -> Tuple[Optional[ParsedOperator], ValidationIssues]:
    issues = ValidationIssues()
    attr_exp = attr_exp.strip()
    sub_or_complex = _get_parsed_group_or_complex_op(
        op_exp=attr_exp,
        parsed_group_ops=parsed_group_ops,
        parsed_complex_ops=parsed_complex_ops,
    )
    if sub_or_complex is not None:
        return sub_or_complex.operator, sub_or_complex.issues

    components = re.split(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', attr_exp)
    if len(components) == 2:
        op_ = _UNARY_ATTR_OPERATORS.get(components[1].lower())
        if op_ is None:
            issues.add(
                issue=ValidationError.unknown_operator(
                    operator_type="unary",
                    operator=_encode_sub_or_complex_into_exp(
                        exp=components[1],
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    ),
                    expression=_encode_sub_or_complex_into_exp(
                        exp=attr_exp,
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    )
                ),
                proceed=False,
            )
        match = _ALLOWED_IDENTIFIERS.fullmatch(components[0])
        if not match:
            issues.add(
                issue=ValidationError.bad_attribute_name(
                    _encode_sub_or_complex_into_exp(
                        exp=components[0],
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    )
                ),
                proceed=False,
            )
        if not issues.can_proceed():
            return None, issues

        if _SUB_ATTR_NAME_REGEX.match(match.group(2)):
            attr_name, sub_attr_name = match.group(2).split(".", 1)
            operator = op.ComplexAttributeOperator(
                attr_name=match.group(1) + attr_name,
                sub_operator=op_(sub_attr_name)
            )
        else:
            operator = op_(components[0])
        return operator, issues

    elif len(components) == 3:
        op_ = _BINARY_ATTR_OPERATORS.get(components[1].lower())
        if op_ is None:
            issues.add(
                issue=ValidationError.unknown_operator(
                    operator_type="binary",
                    operator=_encode_sub_or_complex_into_exp(
                        exp=components[1],
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    ),
                    expression=_encode_sub_or_complex_into_exp(
                        exp=attr_exp,
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    )
                ),
                proceed=False,
            )
        match = _ALLOWED_IDENTIFIERS.fullmatch(components[0])
        if not match:
            issues.add(
                issue=ValidationError.bad_attribute_name(
                    _encode_sub_or_complex_into_exp(
                        exp=components[0],
                        parsed_group_ops=parsed_group_ops,
                        parsed_complex_ops=parsed_complex_ops,
                    )
                ),
                proceed=False,
            )
        value, issues_ = _parse_comparison_value(components[2])
        issues.merge(issues=issues_)

        if not issues.can_proceed():
            return None, issues

        if type(value) not in _ALLOWED_VALUE_TYPES_FOR_BINARY_OPERATORS[op_]:
            issues.add(
                issue=ValidationError.non_compatible_comparison_value(value, op_.SCIM_OP),
                proceed=False,
            )

        if not issues.can_proceed():
            return None, issues

        if _SUB_ATTR_NAME_REGEX.match(match.group(2)):
            attr_name, sub_attr_name = match.group(2).split(".", 1)
            operator = op.ComplexAttributeOperator(
                attr_name=match.group(1) + attr_name,
                sub_operator=op_(sub_attr_name, value)
            )
        else:
            operator = op_(components[0], value)
        return operator, issues

    issues.add(
        issue=ValidationError.unknown_expression(
            _encode_sub_or_complex_into_exp(
                exp=attr_exp,
                parsed_group_ops=parsed_group_ops,
                parsed_complex_ops=parsed_complex_ops,
            )
        ),
        proceed=False,
    )
    return None, issues


def _get_parsed_group_or_complex_op(
    op_exp: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator]
) -> Optional[Union[_ParsedGroupOperator, _ParsedComplexAttributeOperator]]:
    position = _parse_placeholder(op_exp)
    if position is None:
        return None
    if position in parsed_group_ops:
        return parsed_group_ops[position]
    elif position in parsed_complex_ops:
        return parsed_complex_ops[position]
    return None


def _get_placeholder(index: int) -> str:
    return f"|&PLACE_HOLDER_{index}&|"


def _parse_placeholder(exp: str) -> Optional[int]:
    match = _PLACEHOLDER_REGEX.fullmatch(exp)
    if match:
        return int(match.group(1))
    return None


def _encode_sub_or_complex_into_exp(
    exp: str,
    parsed_group_ops: Dict[int, _ParsedGroupOperator],
    parsed_complex_ops: Dict[int, _ParsedComplexAttributeOperator],
):
    encoded = exp
    for match in _PLACEHOLDER_REGEX.finditer(exp):
        index = int(match.group(1))
        if index in parsed_group_ops:
            encoded = encoded.replace(match.group(0), parsed_group_ops[index].expression)
        elif index in parsed_complex_ops:
            encoded = encoded.replace(match.group(0), parsed_complex_ops[index].expression)
    return encoded


def _parse_comparison_value(value: str) -> Tuple[_AllowedOperandValues, ValidationIssues]:
    issues = ValidationIssues()
    if (
        value.startswith("\"") and value.endswith("\"")
        or value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    elif value == "false":
        value = False
    elif value == "true":
        value = True
    elif value == "null":
        value = None
    else:
        try:
            parsed = float(value)
            parsed_int = int(parsed)
            if parsed == parsed_int:
                value = parsed_int
            else:
                value = parsed
        except ValueError:
            issues.add(
                issue=ValidationError.bad_comparison_value(value),
                proceed=False,
            )
    return value, issues
