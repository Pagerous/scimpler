import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from src.parser.error import ValidationError, ValidationIssues
from src.parser.parameters.filter import operator as op

_ATTR_NAME_REGEX = r"\w+"
_SUB_ATTR_NAME_REGEX = r"\w+\.\w+"
_URI_ATTR_PREFIX = rf"(?:[\w.-]+:)*"

_ALLOWED_IDENTIFIERS = re.compile(rf"({_URI_ATTR_PREFIX})?({_ATTR_NAME_REGEX}|{_SUB_ATTR_NAME_REGEX})")

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


ParsedFilter = Union[op.AttributeOperator, op.LogicalOperator, op.ComplexAttributeOperator]


@dataclass
class _ParsedComplexAttributeFilter:
    operator: Optional[op.ComplexAttributeOperator]
    issues: ValidationIssues
    expression: str


@dataclass
class _ParsedSubFilter:
    operator: Optional[Union[op.AttributeOperator, op.LogicalOperator]]
    issues: ValidationIssues
    expression: str


def parse_filter(filter_exp: str) -> Tuple[Optional[ParsedFilter], ValidationIssues]:
    issues = ValidationIssues()
    bracket_open_index = None
    complex_attr_name = ""
    parsed_complex_filters = {}
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
                sub_filter_exp = filter_exp_preprocessed[bracket_open_index+1:i]
                complex_attr_start = bracket_open_index - len(complex_attr_name)
                complex_attr_exp = f"{complex_attr_name}[{sub_filter_exp}]"
                if sub_filter_exp.strip() == "":
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
                    parsed_complex_filters[complex_attr_start] = _ParsedComplexAttributeFilter(
                        operator=None,
                        issues=issues_,
                        expression=complex_attr_exp,
                    )
                else:
                    parsed_complex_sub_filter, issues_ = _parse_filter(
                        filter_exp=sub_filter_exp,
                    )
                    if not issues_.can_proceed():
                        operator = None
                    else:
                        operator = op.ComplexAttributeOperator(complex_attr_name, parsed_complex_sub_filter)
                    parsed_complex_filters[complex_attr_start] = _ParsedComplexAttributeFilter(
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
        for parsed in parsed_complex_filters.values():
            issues.merge(issues=parsed.issues)
        return None, issues

    if bracket_open_index and bracket_open_index not in parsed_complex_filters:
        issues.add(
            issue=ValidationError.no_closing_complex_attribute_bracket(bracket_open_index),
            proceed=False,
        )

    if not issues.can_proceed():
        for parsed in parsed_complex_filters.values():
            issues.merge(issues=parsed.issues)
        return None, issues

    parsed_filter, issues_ = _parse_filter(
        filter_exp=filter_exp,
        parsed_complex_filters=parsed_complex_filters,
    )
    issues.merge(issues=issues_)
    if not issues.can_proceed():
        return None, issues
    return parsed_filter, issues


def _parse_filter(
    filter_exp: str,
    parsed_complex_filters: Optional[Dict[int, _ParsedComplexAttributeFilter]] = None,
) -> Tuple[Optional[ParsedFilter], ValidationIssues]:
    parsed_complex_filters = parsed_complex_filters or {}
    issues = ValidationIssues()
    ignore_processing = False
    bracket_open = False
    bracket_open_index = None
    bracket_cnt = 0
    parsed_sub_filters = {}
    filter_exp_preprocessed = filter_exp
    for i, char in enumerate(filter_exp):
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
            sub_filter_exp = filter_exp[bracket_open_index:i+1]
            parsed_sub_filter, issues_ = _parse_filter(
                filter_exp=sub_filter_exp[1:-1],  # without enclosing brackets
                parsed_complex_filters=parsed_complex_filters,
            )
            parsed_sub_filters[bracket_open_index] = _ParsedSubFilter(
                operator=parsed_sub_filter,
                issues=issues_,
                expression=sub_filter_exp,
            )
            filter_exp_preprocessed = filter_exp_preprocessed.replace(
                sub_filter_exp, _get_placeholder(bracket_open_index), 1
            )
            bracket_open = False
            bracket_open_index = None

    if bracket_open and bracket_open_index not in parsed_sub_filters:
        issues.add(issue=ValidationError.no_closing_bracket(bracket_open_index), proceed=False)

    filter_exp_preprocessed = filter_exp_preprocessed.strip()
    if filter_exp_preprocessed == "":
        issues.add(issue=ValidationError.empty_expression(), proceed=False)

    if not issues.can_proceed():
        return None, issues

    parsed_filter, issues_ = _parse_filter_or_exp(
        or_exp=filter_exp_preprocessed,
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    issues.merge(issues=issues_)
    if not issues.can_proceed():
        return None, issues
    return parsed_filter, issues


def _parse_filter_or_exp(
    or_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], ValidationIssues]:
    issues = ValidationIssues()
    or_operands, issues_ = _split_exp_to_logical_operands(
        filter_exp=or_exp,
        regexp=_OR_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="or",
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    issues.merge(issues=issues_)
    if not or_operands:
        return None, issues

    if len(or_operands) == 1:
        parsed_or_operand, issues_ = _parse_filter_and_exp(
            and_exp=or_operands[0],
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_or_operand = None
        return parsed_or_operand, issues

    parsed_or_operands = []
    for or_operand in or_operands:
        parsed_or_operand, issues_ = _parse_filter_and_exp(
            and_exp=or_operand,
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_or_operand = None
        parsed_or_operands.append(parsed_or_operand)

    if not issues.can_proceed():
        return None, issues
    return op.Or(*parsed_or_operands), issues


def _parse_filter_and_exp(
    and_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], ValidationIssues]:
    issues = ValidationIssues()
    and_operands, issues_ = _split_exp_to_logical_operands(
        filter_exp=and_exp,
        regexp=_AND_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="and",
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    issues.merge(issues=issues_)
    if not and_operands:
        return None, issues

    if len(and_operands) == 1:
        parsed_and_operand, issues_ = _parse_filter_attr_exp(
            attr_exp=and_operands[0],
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            parsed_and_operand = None
        return parsed_and_operand, issues

    parsed_and_operands = []
    for and_operand in and_operands:
        match = _NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
        if match:
            parsed_and_operand, issues_ = _parse_filter_attr_exp(
                attr_exp=match.group(1),
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            issues.merge(issues=issues_)
            if not issues.can_proceed():
                parsed_and_operand = None
            else:
                parsed_and_operand = op.Not(parsed_and_operand)
        else:
            parsed_and_operand, issues_ = _parse_filter_attr_exp(
                attr_exp=and_operand,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            issues.merge(issues=issues_)
            if not issues.can_proceed():
                parsed_and_operand = None
        parsed_and_operands.append(parsed_and_operand)

    if not issues.can_proceed():
        return None, issues
    return op.And(*parsed_and_operands), issues


def _split_exp_to_logical_operands(
    filter_exp: str,
    regexp: re.Pattern[str],
    operator_name: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[List[str], ValidationIssues]:
    issues = ValidationIssues()
    operands = []
    current_position = 0
    matches = list(regexp.finditer(filter_exp))
    for i, match in enumerate(matches):
        left_operand = filter_exp[current_position:match.start()]
        if i == len(matches) - 1:
            right_operand = filter_exp[match.end():]
        else:
            right_operand = filter_exp[match.end():matches[i + 1].start()]

        invalid_expression = None
        if left_operand == right_operand == "":
            invalid_expression = match.group(0).strip()
        elif left_operand == "":
            parsed_filter = _get_parsed_sub_or_complex_filter(
                filter_exp=right_operand,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            if parsed_filter is not None:
                right_expression = parsed_filter.expression
            else:
                right_expression = right_operand
            invalid_expression = (match.group(0) + right_expression).strip()
        elif right_operand == "":
            parsed_filter = _get_parsed_sub_or_complex_filter(
                filter_exp=left_operand,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            if parsed_filter is not None:
                left_expression = parsed_filter.expression
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
        operands = [filter_exp]

    operands = [operand for operand in operands if operand != ""]
    return operands, issues


def _parse_filter_attr_exp(
    attr_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], ValidationIssues]:
    issues = ValidationIssues()
    attr_exp = attr_exp.strip()
    sub_or_complex = _get_parsed_sub_or_complex_filter(
        filter_exp=attr_exp,
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
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
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    ),
                    expression=_encode_sub_or_complex_into_exp(
                        exp=attr_exp,
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    )
                ),
                proceed=False,
            )
        if not _ALLOWED_IDENTIFIERS.fullmatch(components[0]):
            issues.add(
                issue=ValidationError.bad_attribute_name(
                    _encode_sub_or_complex_into_exp(
                        exp=components[0],
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    )
                ),
                proceed=False,
            )
        if not issues.can_proceed():
            return None, issues
        return op_(components[0]), issues
    elif len(components) == 3:
        op_ = _BINARY_ATTR_OPERATORS.get(components[1].lower())
        if op_ is None:
            issues.add(
                issue=ValidationError.unknown_operator(
                    operator_type="binary",
                    operator=_encode_sub_or_complex_into_exp(
                        exp=components[1],
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    ),
                    expression=_encode_sub_or_complex_into_exp(
                        exp=attr_exp,
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    )
                ),
                proceed=False,
            )
        if not _ALLOWED_IDENTIFIERS.fullmatch(components[0]):
            issues.add(
                issue=ValidationError.bad_attribute_name(
                    _encode_sub_or_complex_into_exp(
                        exp=components[0],
                        parsed_sub_filters=parsed_sub_filters,
                        parsed_complex_filters=parsed_complex_filters,
                    )
                ),
                proceed=False,
            )
        value, issues_ = _parse_comparison_value(components[2])
        issues.merge(issues=issues_)
        if not issues.can_proceed():
            return None, issues
        return op_(components[0], value), issues

    issues.add(
        issue=ValidationError.unknown_expression(
            _encode_sub_or_complex_into_exp(
                exp=attr_exp,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
        ),
        proceed=False,
    )
    return None, issues


def _get_parsed_sub_or_complex_filter(
    filter_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter]
) -> Optional[Union[_ParsedSubFilter, _ParsedComplexAttributeFilter]]:
    position = _parse_placeholder(filter_exp)
    if position is None:
        return None
    if position in parsed_sub_filters:
        return parsed_sub_filters[position]
    elif position in parsed_complex_filters:
        return parsed_complex_filters[position]
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
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
):
    encoded = exp
    for match in _PLACEHOLDER_REGEX.finditer(exp):
        index = int(match.group(1))
        if index in parsed_sub_filters:
            encoded = encoded.replace(match.group(0), parsed_sub_filters[index].expression)
        elif index in parsed_complex_filters:
            encoded = encoded.replace(match.group(0), parsed_complex_filters[index].expression)
    return encoded


_AllowedOperandValues = Union[str, bool, int, float, None]


def _parse_comparison_value(value: str) -> Tuple[_AllowedOperandValues, ValidationIssues]:
    issues = ValidationIssues()
    if value.startswith("\"") and value.endswith("\""):
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
