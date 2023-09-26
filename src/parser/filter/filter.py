import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from src.parser.error import ValidationError
from src.parser.filter import operator as op

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
    errors: List[ValidationError]
    expression: str


@dataclass
class _ParsedSubFilter:
    operator: Optional[Union[op.AttributeOperator, op.LogicalOperator]]
    errors: List[ValidationError]
    expression: str


def parse_filter(filter_exp: str) -> Tuple[Optional[ParsedFilter], List[ValidationError]]:
    errors = []
    bracket_open_index = None
    complex_attr_name = ""
    parsed_complex_filters = {}
    filter_exp_preprocessed = filter_exp
    ignore_processing = False
    errors_ = []
    for i, char in enumerate(filter_exp_preprocessed):
        if char == "\"":
            ignore_processing = not ignore_processing
        if ignore_processing:
            continue

        if (re.match(r"\w", char) or char in ":.") and bracket_open_index is None:
            complex_attr_name += char
        elif char == "[":
            if bracket_open_index is not None:
                errors.append(ValidationError.inner_complex_attribute_or_square_bracket())
                break
            else:
                bracket_open_index = i
        elif char == "]":
            if bracket_open_index is None:
                errors.append(ValidationError.no_opening_complex_attribute_bracket(i))
            else:
                sub_filter_exp = filter_exp_preprocessed[bracket_open_index+1:i]
                complex_attr_start = bracket_open_index - len(complex_attr_name)
                complex_attr_exp = f"{complex_attr_name}[{sub_filter_exp}]"
                if sub_filter_exp.strip() == "":
                    errors_.append(
                        ValidationError.empty_complex_attribute_expression(complex_attr_name, complex_attr_start)
                    )
                if complex_attr_name == "":
                    errors_.append(
                        ValidationError.complex_attribute_without_top_level_attribute(complex_attr_exp)
                    )
                elif not _ALLOWED_IDENTIFIERS.fullmatch(complex_attr_name):
                    errors_.append(ValidationError.bad_attribute_name(complex_attr_name))

                if errors_:
                    parsed_complex_filters[complex_attr_start] = _ParsedComplexAttributeFilter(
                        operator=None,
                        errors=errors_,
                        expression=complex_attr_exp,
                    )
                else:
                    parsed_complex_sub_filter, errors_ = _parse_filter(
                        filter_exp=sub_filter_exp,
                    )
                    if errors_:
                        operator = None
                    else:
                        operator = op.ComplexAttributeOperator(complex_attr_name, parsed_complex_sub_filter)
                    parsed_complex_filters[complex_attr_start] = _ParsedComplexAttributeFilter(
                        operator=operator,
                        errors=errors_,
                        expression=complex_attr_exp,
                    )
                filter_exp = filter_exp.replace(
                    complex_attr_exp, _get_placeholder(complex_attr_start), 1
                )
            bracket_open_index = None
            complex_attr_name = ""
            errors_ = []
        elif bracket_open_index is None:
            complex_attr_name = ""
            errors_ = []

    if errors:
        for parsed in parsed_complex_filters.values():
            errors.extend(parsed.errors)
        return None, errors

    if bracket_open_index and bracket_open_index not in parsed_complex_filters:
        errors.append(ValidationError.no_closing_complex_attribute_bracket(bracket_open_index))

    if errors:
        for parsed in parsed_complex_filters.values():
            errors.extend(parsed.errors)
        return None, errors

    return _parse_filter(
        filter_exp=filter_exp,
        parsed_complex_filters=parsed_complex_filters
    )


def _parse_filter(
    filter_exp: str,
    parsed_complex_filters: Optional[Dict[int, _ParsedComplexAttributeFilter]] = None,
) -> Tuple[Optional[ParsedFilter], List[ValidationError]]:
    parsed_complex_filters = parsed_complex_filters or {}
    errors = []
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
                errors.append(ValidationError.no_opening_bracket(i))
        if bracket_open and bracket_cnt == 0:
            sub_filter_exp = filter_exp[bracket_open_index:i+1]
            parsed_sub_filter, sub_filter_errors = _parse_filter(
                filter_exp=sub_filter_exp[1:-1],  # without enclosing brackets
                parsed_complex_filters=parsed_complex_filters,
            )
            parsed_sub_filters[bracket_open_index] = _ParsedSubFilter(
                operator=parsed_sub_filter,
                errors=sub_filter_errors,
                expression=sub_filter_exp,
            )
            filter_exp_preprocessed = filter_exp_preprocessed.replace(
                sub_filter_exp, _get_placeholder(bracket_open_index), 1
            )
            bracket_open = False
            bracket_open_index = None

    if bracket_open and bracket_open_index not in parsed_sub_filters:
        errors.append(ValidationError.no_closing_bracket(bracket_open_index))

    filter_exp_preprocessed = filter_exp_preprocessed.strip()
    if filter_exp_preprocessed == "":
        errors.append(ValidationError.empty_expression())

    if errors:
        return None, errors

    return _parse_filter_or_exp(
        or_exp=filter_exp_preprocessed,
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )


def _parse_filter_or_exp(
    or_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], List[ValidationError]]:
    errors = []
    or_operands, errors_ = _split_exp_to_logical_operands(
        filter_exp=or_exp,
        regexp=_OR_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="or",
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    errors.extend(errors_)
    if not or_operands:
        return None, errors

    if len(or_operands) == 1:
        parsed_or_operand, errors_ = _parse_filter_and_exp(
            and_exp=or_operands[0],
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        errors.extend(errors_)
        if errors:
            parsed_or_operand = None
        return parsed_or_operand, errors

    parsed_or_operands = []
    for or_operand in or_operands:
        parsed_or_operand, errors_ = _parse_filter_and_exp(
            and_exp=or_operand,
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        errors.extend(errors_)
        if errors:
            parsed_or_operand = None
        parsed_or_operands.append(parsed_or_operand)
    if errors:
        return None, errors
    return op.Or(*parsed_or_operands), []


def _parse_filter_and_exp(
    and_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], List[ValidationError]]:
    errors = []
    and_operands, errors_ = _split_exp_to_logical_operands(
        filter_exp=and_exp,
        regexp=_AND_LOGICAL_OPERATOR_SPLIT_REGEX,
        operator_name="and",
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    errors.extend(errors_)
    if not and_operands:
        return None, errors

    if len(and_operands) == 1:
        parsed_and_operand, errors_ = _parse_filter_attr_exp(
            attr_exp=and_operands[0],
            parsed_sub_filters=parsed_sub_filters,
            parsed_complex_filters=parsed_complex_filters,
        )
        errors.extend(errors_)
        if errors:
            parsed_and_operand = None
        return parsed_and_operand, errors

    parsed_and_operands = []
    for and_operand in and_operands:
        match = _NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
        if match:
            parsed_and_operand, errors_ = _parse_filter_attr_exp(
                attr_exp=match.group(1),
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            errors.extend(errors_)
            if errors:
                parsed_and_operand = None
            else:
                parsed_and_operand = op.Not(parsed_and_operand)
        else:
            parsed_and_operand, errors_ = _parse_filter_attr_exp(
                attr_exp=and_operand,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
            errors.extend(errors_)
            if errors:
                parsed_and_operand = None
        parsed_and_operands.append(parsed_and_operand)
    if errors:
        return None, errors
    return op.And(*parsed_and_operands), []


def _split_exp_to_logical_operands(
    filter_exp: str,
    regexp: re.Pattern[str],
    operator_name: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[List[str], List[ValidationError]]:
    errors = []
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
            errors.append(
                ValidationError.missing_operand_for_operator(
                    operator=operator_name,
                    expression=invalid_expression,
                ),
            )

        if i == 0:
            operands.append(left_operand)
        operands.append(right_operand)
        current_position = match.end()

    if not matches:
        operands = [filter_exp]

    operands = [operand for operand in operands if operand != ""]
    return operands, errors


def _parse_filter_attr_exp(
    attr_exp: str,
    parsed_sub_filters: Dict[int, _ParsedSubFilter],
    parsed_complex_filters: Dict[int, _ParsedComplexAttributeFilter],
) -> Tuple[Optional[ParsedFilter], List[ValidationError]]:
    errors = []
    attr_exp = attr_exp.strip()
    sub_or_complex = _get_parsed_sub_or_complex_filter(
        filter_exp=attr_exp,
        parsed_sub_filters=parsed_sub_filters,
        parsed_complex_filters=parsed_complex_filters,
    )
    if sub_or_complex is not None:
        return sub_or_complex.operator, sub_or_complex.errors

    components = re.split(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', attr_exp)
    if len(components) == 2:
        op_ = _UNARY_ATTR_OPERATORS.get(components[1])
        if op_ is None:
            errors.append(
                ValidationError.unknown_operator(
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
                )
            )
        if not _ALLOWED_IDENTIFIERS.fullmatch(components[0]):
            errors.append(
                ValidationError.bad_attribute_name(components[0])
            )
        if errors:
            return None, errors
        return op_(components[0]), []
    elif len(components) == 3:
        op_ = _BINARY_ATTR_OPERATORS.get(components[1])
        if op_ is None:
            errors.append(
                ValidationError.unknown_operator(
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
                )
            )
        if not _ALLOWED_IDENTIFIERS.fullmatch(components[0]):
            errors.append(ValidationError.bad_attribute_name(components[0]))
        if errors:
            return None, errors
        return op_(components[0], components[2]), []
    return None, [
        ValidationError.unknown_expression(
            _encode_sub_or_complex_into_exp(
                exp=attr_exp,
                parsed_sub_filters=parsed_sub_filters,
                parsed_complex_filters=parsed_complex_filters,
            )
        )
    ]


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
