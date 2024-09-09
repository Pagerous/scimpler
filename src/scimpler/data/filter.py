import re
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Iterable,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import TypeAlias

from scimpler._registry import binary_operators, unary_operators
from scimpler.data import operator as op
from scimpler.data.attrs import Complex
from scimpler.data.identifiers import AttrRep, AttrRepFactory, BoundedAttrRep
from scimpler.data.schemas import BaseSchema
from scimpler.data.scim_data import ScimData
from scimpler.data.utils import (
    OP_REGEX,
    decode_placeholders,
    deserialize_comparison_value,
    deserialize_placeholder,
    encode_strings,
    get_placeholder,
)
from scimpler.error import ScimErrorType, ValidationError, ValidationIssues

OR_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\bor\b\s*", flags=re.DOTALL)
AND_LOGICAL_OPERATOR_SPLIT_REGEX = re.compile(r"\s*\band\b\s*", flags=re.DOTALL)
NOT_LOGICAL_OPERATOR_REGEX = re.compile(r"\s*\bnot\b\s*(.*)", flags=re.DOTALL)
COMPLEX_OPERATOR_REGEX = re.compile(r"([\w:.]+)\[(.*?)]", flags=re.DOTALL)
GROUP_OPERATOR_REGEX = re.compile(r"\((?:[^()]|\([^()]*\))*\)", flags=re.DOTALL)

_AllowedOperandValues: TypeAlias = Union[str, bool, int, float, None]


TOperator = TypeVar("TOperator", bound=op.Operator)


@dataclass
class _ValidatedComplexOperator:
    issues: ValidationIssues
    expression: str
    placeholder: str


@dataclass
class _ValidatedGroupOperator:
    issues: ValidationIssues
    expression: str
    placeholder: str


class Filter(Generic[TOperator]):
    """
    Data filter supporting SCIM and custom operators.

    Args:
        operator: Underlying filter operator, used for data filtering.

    Examples:
        >>> username_filter = Filter.deserialize("userName eq 'Pagerous'")
        >>> username_filter({"userName": "Pagerous"})
        True
        >>> username_filter({"userName": "NotPagerous"})
        False
    """

    def __init__(self, operator: TOperator):
        self._operator = operator

    @property
    def attr_reps(self) -> list[AttrRep]:
        """
        List of bounded and unbounded attribute representations
        included in the filter. Useful to determine if there is
        enough data to use filter, since no data means no match
        (except for `not pr` operator).
        """
        return self._get_attr_reps(self._operator)

    @staticmethod
    def _get_attr_reps(operator) -> list[AttrRep]:
        reps = []

        def get_sub_attr_name(sub_rep_):
            return sub_rep_.sub_attr if sub_rep_.is_sub_attr else sub_rep_.attr

        def extend_reps(reps_: Iterable[AttrRep]):
            for rep_ in reps_:
                if rep_ not in reps:
                    reps.append(rep_)

        if isinstance(operator, op.AttributeOperator):
            reps.append(operator.attr_rep)
        elif isinstance(operator, op.ComplexAttributeOperator):
            rep = operator.attr_rep
            sub_reps: Iterable[Union[AttrRep, BoundedAttrRep]]
            if isinstance(rep, BoundedAttrRep):
                sub_reps = [
                    BoundedAttrRep(
                        schema=rep.schema,
                        attr=rep.attr,
                        sub_attr=get_sub_attr_name(sub_rep),
                    )
                    for sub_rep in Filter._get_attr_reps(operator.sub_operator)
                ]
            else:
                sub_reps = [
                    AttrRep(attr=rep.attr, sub_attr=get_sub_attr_name(sub_rep))
                    for sub_rep in Filter._get_attr_reps(operator.sub_operator)
                ]
            extend_reps(sub_reps)
        elif isinstance(operator, op.LogicalOperator):
            for sub_op in operator.sub_operators:
                extend_reps(Filter._get_attr_reps(sub_op))
        return reps

    @property
    def operator(self) -> TOperator:
        """
        Underlying filter operator, used for data filtering.
        """
        return self._operator

    @classmethod
    def validate(cls, filter_exp: str) -> ValidationIssues:
        """
        Validates the filter expression syntax, according to RFC-7644.

        Args:
            filter_exp: Filter expression to validate.

        Returns:
            Validation issues.
        """
        filter_exp, placeholders = encode_strings(filter_exp)
        issues = Filter._validate_complex_group_operators(filter_exp, placeholders)

        if not issues.can_proceed():
            for validated in placeholders.values():
                if isinstance(validated, _ValidatedComplexOperator):
                    issues.merge(issues=validated.issues)
            return issues

        for validated in placeholders.values():
            if isinstance(validated, _ValidatedComplexOperator):
                filter_exp = filter_exp.replace(validated.expression, validated.placeholder, 1)

        issues.merge(Filter._validate_operator(filter_exp, placeholders))
        return issues

    @staticmethod
    def _validate_complex_group_operators(
        filter_exp: str, placeholders: dict[str, Any]
    ) -> ValidationIssues:
        issues = ValidationIssues()
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
                issues.merge(
                    Filter._validate_complex_group_operator(
                        filter_exp=filter_exp_iter_copy,
                        complex_attr_rep_exp=complex_attr_rep,
                        placeholders=placeholders,
                        bracket_open_index=bracket_open_index,
                        string_pos=i,
                    )
                )
                bracket_open_index = None
                complex_attr_rep = ""
            elif bracket_open_index is None:
                complex_attr_rep = ""
        if issues.can_proceed() and bracket_open_index is not None:
            issues.add_error(
                issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                proceed=False,
            )
        return issues

    @staticmethod
    def _validate_complex_group_operator(
        filter_exp: str,
        complex_attr_rep_exp: str,
        placeholders: dict[str, Any],
        bracket_open_index: Optional[int],
        string_pos: int,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if bracket_open_index is None:
            issues.add_error(
                issue=ValidationError.complex_attribute_bracket_not_opened_or_closed(),
                proceed=False,
            )
        else:
            sub_ops_exp = filter_exp[bracket_open_index + 1 : string_pos]
            complex_attr_exp = f"{complex_attr_rep_exp}[{sub_ops_exp}]"
            issues_ = ValidationIssues()
            if sub_ops_exp.strip() == "":
                issues_.add_error(
                    issue=ValidationError.empty_complex_attribute_expression(complex_attr_rep_exp),
                    proceed=False,
                )
            try:
                attr_rep = AttrRepFactory.deserialize(complex_attr_rep_exp)
                if isinstance(attr_rep, AttrRep) and attr_rep.is_sub_attr:
                    issues_.add_error(
                        issue=ValidationError.complex_sub_attribute(
                            attr=attr_rep.attr, sub_attr=attr_rep.sub_attr
                        ),
                        proceed=False,
                    )
            except ValueError:
                issues_.add_error(
                    issue=ValidationError.bad_attribute_name(complex_attr_rep_exp),
                    proceed=False,
                )
            id_, placeholder = get_placeholder()
            if not issues_.can_proceed():
                placeholders[id_] = _ValidatedComplexOperator(
                    issues=issues_,
                    expression=complex_attr_exp,
                    placeholder=placeholder,
                )
            else:
                placeholders[id_] = _ValidatedComplexOperator(
                    issues=Filter._validate_operator(sub_ops_exp, placeholders),
                    expression=complex_attr_exp,
                    placeholder=placeholder,
                )
        return issues

    @staticmethod
    def _validate_operator(exp: str, placeholders: dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        is_bracket_open = False
        bracket_open_index = None
        placeholder_ids = []
        bracket_count = 0
        op_exp_preprocessed = exp
        for i, char in enumerate(exp):
            (is_bracket_open, bracket_open_index, bracket_count, placeholder_id) = (
                Filter._process_grouping_operator_character(
                    issues=issues,
                    filter_exp=exp,
                    placeholders=placeholders,
                    char=char,
                    char_pos=i,
                    is_bracket_open=is_bracket_open,
                    bracket_open_index=bracket_open_index,
                    bracket_count=bracket_count,
                )
            )
            if placeholder_id is not None:
                placeholder_ids.append(placeholder_id)

        if is_bracket_open and bracket_open_index is not None:
            issues.add_error(issue=ValidationError.bracket_not_opened_or_closed(), proceed=False)

        if not issues.can_proceed():
            return issues

        for placeholder_id in placeholder_ids:
            validated = placeholders[placeholder_id]
            op_exp_preprocessed = op_exp_preprocessed.replace(
                validated.expression, validated.placeholder, 1
            )

        op_exp_preprocessed = op_exp_preprocessed.strip()
        if op_exp_preprocessed == "":
            issues.add_error(issue=ValidationError.empty_filter_expression(), proceed=False)

        if not issues.can_proceed():
            return issues

        issues.merge(Filter._validate_op_or_exp(op_exp_preprocessed, placeholders))

        for _, errors in issues.errors:
            for error in errors:
                error.scim_error = ScimErrorType.INVALID_FILTER
        return issues

    @staticmethod
    def _process_grouping_operator_character(
        issues: ValidationIssues,
        filter_exp: str,
        placeholders: dict[str, Any],
        char: str,
        char_pos: int,
        is_bracket_open: bool,
        bracket_open_index: Optional[int],
        bracket_count: int,
    ):
        placeholder_id = None
        if char == "(":
            if not is_bracket_open:
                is_bracket_open = True
                bracket_open_index = char_pos
            bracket_count += 1
        elif char == ")":
            if is_bracket_open:
                bracket_count -= 1
            else:
                issues.add_error(
                    issue=ValidationError.bracket_not_opened_or_closed(), proceed=False
                )
        if is_bracket_open and bracket_count == 0:
            group_op_exp = filter_exp[bracket_open_index : char_pos + 1]
            issues_ = Filter._validate_operator(
                exp=group_op_exp[1:-1],  # without enclosing brackets
                placeholders=placeholders,
            )
            placeholder_id, placeholder = get_placeholder()
            placeholders[placeholder_id] = _ValidatedGroupOperator(
                issues=issues_,
                expression=group_op_exp,
                placeholder=placeholder,
            )
            is_bracket_open = False
            bracket_open_index = None
        return is_bracket_open, bracket_open_index, bracket_count, placeholder_id

    @staticmethod
    def _validate_op_or_exp(exp: str, placeholders: dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        or_operands, issues_ = Filter._validate_logical_operands(
            exp=exp,
            regexp=OR_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="or",
            placeholders=placeholders,
        )
        issues.merge(issues=issues_)
        for or_operand in or_operands:
            issues.merge(Filter._validate_op_and_exp(or_operand, placeholders))
        return issues

    @staticmethod
    def _validate_op_and_exp(exp: str, placeholders: dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        and_operands, issues_ = Filter._validate_logical_operands(
            exp=exp,
            regexp=AND_LOGICAL_OPERATOR_SPLIT_REGEX,
            operator_name="and",
            placeholders=placeholders,
        )
        issues.merge(issues=issues_)

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
        placeholders: dict[str, Any],
    ) -> tuple[list[str], ValidationIssues]:
        issues = ValidationIssues()
        operands = []
        current_position = 0
        matches = list(regexp.finditer(exp))
        for i, operand_match in enumerate(matches):
            left_operand = exp[current_position : operand_match.start()]
            if i == len(matches) - 1:
                right_operand = exp[operand_match.end() :]
            else:
                right_operand = exp[operand_match.end() : matches[i + 1].start()]

            issues.merge(
                issues=Filter._validate_operands_pair(
                    left_operand=left_operand,
                    right_operand=right_operand,
                    op_name=operator_name,
                    placeholders=placeholders,
                )
            )

            if i == 0:
                operands.append(left_operand)
            operands.append(right_operand)
            current_position = operand_match.end()

        if not matches:
            operands = [exp]

        operands = [operand for operand in operands if operand != ""]
        return operands, issues

    @staticmethod
    def _validate_operands_pair(
        left_operand: str,
        right_operand: str,
        op_name: str,
        placeholders: dict[str, Any],
    ) -> ValidationIssues:
        issues = ValidationIssues()
        invalid_exp = None
        if left_operand == "":
            if (placeholder := deserialize_placeholder(right_operand)) and (
                deserialized_op := placeholders.get(placeholder)
            ):
                right_expression = deserialized_op.expression
            else:
                right_expression = right_operand
            invalid_exp = f"{op_name} {right_expression}".strip()
        elif right_operand == "":
            if (placeholder := deserialize_placeholder(left_operand)) and (
                deserialized_op := placeholders.get(placeholder)
            ):
                left_expression = deserialized_op.expression
            else:
                left_expression = left_operand
            invalid_exp = f"{left_expression} {op_name}".strip()

        if invalid_exp is not None:
            issues.add_error(
                issue=ValidationError.missing_operand_for_operator(
                    operator=op_name,
                    expression=decode_placeholders(invalid_exp, placeholders),
                ),
                proceed=False,
            )
        return issues

    @staticmethod
    def _validate_op_attr_exp(attr_exp: str, placeholders: dict[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        attr_exp = attr_exp.strip()
        if (placeholder := deserialize_placeholder(attr_exp)) and (
            sub_or_complex := placeholders.get(placeholder)
        ) is not None:
            return sub_or_complex.issues

        components = OP_REGEX.split(attr_exp)
        if len(components) == 2:
            issues.merge(
                Filter._validate_unary_op_attr_exp(
                    attr_exp=attr_exp,
                    attr_rep_exp=components[0],
                    op_exp=components[1],
                    placeholders=placeholders,
                )
            )
            return issues
        elif len(components) == 3:
            issues.merge(
                Filter._validate_binary_op_attr_exp(
                    attr_exp=attr_exp,
                    attr_rep_exp=components[0],
                    op_exp=components[1],
                    value_exp=components[2],
                    placeholders=placeholders,
                )
            )
            return issues

        issues.add_error(
            issue=ValidationError.unknown_expression(decode_placeholders(attr_exp, placeholders)),
            proceed=False,
        )
        return issues

    @staticmethod
    def _validate_unary_op_attr_exp(
        attr_exp: str, attr_rep_exp: str, op_exp: str, placeholders: dict[str, Any]
    ) -> ValidationIssues:
        issues = ValidationIssues()
        op_exp = op_exp.lower()
        op_ = unary_operators.get(op_exp)
        if op_ is None:
            if op_exp in binary_operators:
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
                        operator=decode_placeholders(op_exp, placeholders),
                        expression=decode_placeholders(attr_exp, placeholders),
                    ),
                    proceed=False,
                )
        attr_rep = decode_placeholders(attr_rep_exp, placeholders)
        issues.merge(AttrRepFactory.validate(attr_rep))
        return issues

    @staticmethod
    def _validate_binary_op_attr_exp(
        attr_exp: str, attr_rep_exp: str, op_exp: str, value_exp: str, placeholders: dict[str, Any]
    ) -> ValidationIssues:
        issues = ValidationIssues()
        op_ = binary_operators.get(op_exp.lower())
        if op_ is None:
            issues.add_error(
                issue=ValidationError.unknown_operator(
                    operator=decode_placeholders(op_exp, placeholders),
                    expression=decode_placeholders(attr_exp, placeholders),
                ),
                proceed=False,
            )
        attr_rep = decode_placeholders(attr_rep_exp, placeholders)
        issues.merge(AttrRepFactory.validate(attr_rep))
        value = decode_placeholders(value_exp, placeholders)
        try:
            value = deserialize_comparison_value(value)
        except ValueError:
            issues.add_error(
                issue=ValidationError.bad_operand(decode_placeholders(value_exp, placeholders)),
                proceed=False,
            )
        if op_ and type(value) not in op_.supported_types:
            issues.add_error(
                issue=ValidationError.non_compatible_operand(value, op_.op),
                proceed=False,
            )
        return issues

    def serialize(self) -> str:
        """
        Serializes `Filter` to string filter expression.
        """
        output = self._serialize(self._operator)
        if output.startswith("(") and output.endswith(")"):
            output = output[1:-1]
        return output

    @staticmethod
    def _serialize(operator) -> str:
        if isinstance(operator, op.AttributeOperator):
            output = f"{operator.attr_rep} {operator.op}"
            if isinstance(operator, op.BinaryAttributeOperator):
                output += f" {operator.value!r}"
            return output

        if isinstance(operator, op.ComplexAttributeOperator):
            return f"{operator.attr_rep}[{Filter._serialize(operator.sub_operator)}]"

        if isinstance(operator, op.Not):
            return f"{operator.op} {Filter._serialize(operator.sub_operators[0])}"

        if isinstance(operator, (op.And, op.Or)):
            output = f" {operator.op} ".join(
                [Filter._serialize(sub_operator) for sub_operator in operator.sub_operators]
            )
            return f"({output})"

        raise TypeError(f"unsupported filter type '{type(operator).__name__}'")

    @classmethod
    def deserialize(cls, filter_exp: str) -> "Filter":
        """
        Deserializes the filter expression.

        Args:
            filter_exp: filter expression to be deserialized.

        Raises:
            ValueError: If provided filter expression is invalid.

        Returns:
            Deserialized filter.
        """
        try:
            return cls._deserialize(filter_exp)
        except Exception:
            raise ValueError("invalid filter expression")

    @classmethod
    def _deserialize(cls, filter_exp: str) -> "Filter":
        filter_exp, placeholders = encode_strings(filter_exp)
        for match in COMPLEX_OPERATOR_REGEX.finditer(filter_exp):
            complex_attr_rep = match.group(1)
            attr_rep = AttrRepFactory.deserialize(complex_attr_rep)
            if isinstance(attr_rep, AttrRep) and attr_rep.is_sub_attr:
                raise ValueError("invalid filter expression")
            sub_op_exp = match.group(2)
            deserialized_sub_op = cast(
                Union[op.AttributeOperator, op.LogicalOperator],
                Filter._deserialize_operator(sub_op_exp, placeholders, in_complex_group=True),
            )
            id_, placeholder = get_placeholder()
            placeholders[id_] = op.ComplexAttributeOperator(
                attr_rep=attr_rep,
                sub_operator=deserialized_sub_op,
            )
            filter_exp = filter_exp.replace(match.group(0), placeholder, 1)

        deserialized_op = Filter._deserialize_operator(
            filter_exp, placeholders, in_complex_group=False
        )
        return cls(cast(TOperator, deserialized_op))

    @staticmethod
    def _deserialize_operator(
        exp: str, placeholders: dict[str, Any], in_complex_group: bool
    ) -> op.Operator:
        for match in GROUP_OPERATOR_REGEX.finditer(exp):
            sub_op_exp = match.group(0)
            deserialized_op = Filter._deserialize_operator(
                exp=sub_op_exp[1:-1],  # without enclosing brackets
                placeholders=placeholders,
                in_complex_group=in_complex_group,
            )
            id_, placeholder = get_placeholder()
            placeholders[id_] = deserialized_op
            exp = exp.replace(sub_op_exp, placeholder, 1)
        return Filter._deserialize_op_or_exp(exp, placeholders, in_complex_group)

    @staticmethod
    def _deserialize_op_or_exp(
        exp: str, placeholders: dict[str, Any], in_complex_group: bool
    ) -> op.Operator:
        or_operands = Filter._split_exp_to_logical_operands(
            exp=exp,
            regexp=OR_LOGICAL_OPERATOR_SPLIT_REGEX,
        )
        deserialized_or_operands = []
        for or_operand in or_operands:
            deserialized_or_operands.append(
                Filter._deserialize_op_and_exp(or_operand, placeholders, in_complex_group)
            )
        if len(deserialized_or_operands) == 1:
            return deserialized_or_operands[0]
        return op.Or(*deserialized_or_operands)

    @staticmethod
    def _deserialize_op_and_exp(
        exp: str,
        placeholders: dict[str, Any],
        in_complex_group: bool,
    ) -> op.Operator:
        and_operands = Filter._split_exp_to_logical_operands(
            exp=exp,
            regexp=AND_LOGICAL_OPERATOR_SPLIT_REGEX,
        )
        deserialized_and_operands: list[op.Operator] = []
        for and_operand in and_operands:
            match = NOT_LOGICAL_OPERATOR_REGEX.match(and_operand)
            if match:
                deserialized_and_operands.append(
                    op.Not(
                        Filter._deserialize_op_attr_exp(
                            match.group(1), placeholders, in_complex_group
                        )
                    )
                )
            else:
                deserialized_and_operands.append(
                    Filter._deserialize_op_attr_exp(and_operand, placeholders, in_complex_group)
                )
        if len(deserialized_and_operands) == 1:
            return deserialized_and_operands[0]
        return op.And(*deserialized_and_operands)

    @staticmethod
    def _split_exp_to_logical_operands(exp: str, regexp: re.Pattern[str]) -> list[str]:
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
    def _deserialize_op_attr_exp(
        exp: str,
        placeholders: dict[str, Any],
        in_complex_group: bool,
    ) -> op.Operator:
        exp = exp.strip()
        if (placeholder := deserialize_placeholder(exp)) and (
            sub_or_complex := placeholders.get(placeholder)
        ) is not None:
            return sub_or_complex
        components = OP_REGEX.split(exp)
        assert len(components) in [2, 3]

        op_: Union[Type[op.UnaryAttributeOperator], Type[op.BinaryAttributeOperator]]
        if len(components) == 2:
            op_exp = components[1].lower()
            op_ = unary_operators[op_exp]
            attr_rep = AttrRepFactory.deserialize(components[0])
            if in_complex_group and isinstance(attr_rep, AttrRep):
                attr_rep = AttrRep(
                    attr=attr_rep.sub_attr if attr_rep.is_sub_attr else attr_rep.attr
                )
            return op_(attr_rep)
        op_ = binary_operators[components[1].lower()]
        value = deserialize_comparison_value(decode_placeholders(components[2], placeholders))

        attr_rep = AttrRepFactory.deserialize(components[0])
        if in_complex_group and isinstance(attr_rep, AttrRep):
            attr_rep = AttrRep(attr=attr_rep.sub_attr if attr_rep.is_sub_attr else attr_rep.attr)
        return op_(attr_rep, value)

    def __call__(
        self,
        data: MutableMapping[str, Any],
        schema_or_complex: Union[BaseSchema, Complex],
    ) -> bool:
        """
        Matches the data against the filter.

        Args:
            data: Data to be matched.
            schema_or_complex: Schema or `Complex` attribute, which describes
                the provided data.

        Returns:
            Flag indicating whether the data matches the filter.
        """
        return self._operator.match(ScimData(data), schema_or_complex)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Filter):
            return False
        return ScimData(self.to_dict()) == ScimData(other.to_dict())

    def to_dict(self) -> dict:
        """
        Convert the filter to a dictionary.
        """
        return self._to_dict(self._operator)

    @staticmethod
    def _to_dict(operator):
        if isinstance(operator, op.AttributeOperator):
            filter_dict = {
                "op": operator.op,
                "attr": str(operator.attr_rep),
            }
            if isinstance(operator, op.BinaryAttributeOperator):
                filter_dict["value"] = operator.value
            return filter_dict

        if isinstance(operator, op.ComplexAttributeOperator):
            return {
                "op": "complex",
                "attr": str(operator.attr_rep),
                "sub_op": Filter._to_dict(operator.sub_operator),
            }

        if isinstance(operator, op.Not):
            return {
                "op": operator.op,
                "sub_op": Filter._to_dict(operator.sub_operators[0]),
            }

        if isinstance(operator, (op.And, op.Or)):
            return {
                "op": operator.op,
                "sub_ops": [
                    Filter._to_dict(sub_operator) for sub_operator in operator.sub_operators
                ],
            }
        raise TypeError(f"unsupported filter type '{type(operator).__name__}'")
