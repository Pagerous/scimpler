import abc
import operator
from typing import Any, Callable, Generator, Generic, Optional, TypeVar, Union

from src.container import AttrRep, BoundedAttrRep, Invalid, Missing, SCIMDataContainer
from src.data.attributes import Attribute, AttributeWithCaseExact, Complex, String
from src.data.schemas import BaseSchema
from src.registry import converters

TSchemaOrComplex = TypeVar("TSchemaOrComplex", bound=[])


class LogicalOperator(abc.ABC, Generic[TSchemaOrComplex]):
    SCIM_OP = None

    @abc.abstractmethod
    def match(
        self,
        value: Optional[SCIMDataContainer],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """Docs placeholder."""


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(
        self,
        *sub_operators: Union["LogicalOperator", "AttributeOperator", "ComplexAttributeOperator"],
    ):
        self._sub_operators = list(sub_operators)

    @property
    def sub_operators(
        self,
    ) -> list[Union["LogicalOperator", "AttributeOperator", "ComplexAttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(
        self,
        value: SCIMDataContainer,
        schema_or_complex: TSchemaOrComplex,
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, schema_or_complex)
            else:
                yield sub_operator.match(value.get(sub_operator.attr_rep), schema_or_complex)


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(
        self,
        value: Optional[SCIMDataContainer],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or SCIMDataContainer()
        for match in self._collect_matches(value, schema_or_complex):
            if not match:
                return False
        return True


class Or(MultiOperandLogicalOperator):
    SCIM_OP = "or"

    def match(
        self,
        value: Optional[SCIMDataContainer],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or SCIMDataContainer()
        for match in self._collect_matches(value, schema_or_complex):
            if match:
                return True
        return False


TNotSubOperator = TypeVar(
    "TNotSubOperator", bound=Union[MultiOperandLogicalOperator, "AttributeOperator"]
)


class Not(LogicalOperator):
    SCIM_OP = "not"

    def __init__(self, sub_operator: TNotSubOperator):
        self._sub_operator = sub_operator

    @property
    def sub_operator(self) -> TNotSubOperator:
        return self._sub_operator

    def match(
        self,
        value: Optional[SCIMDataContainer],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or SCIMDataContainer()
        if isinstance(self._sub_operator, LogicalOperator):
            match = self._sub_operator.match(value, schema_or_complex)
        else:
            match = self._sub_operator.match(
                value.get(self._sub_operator.attr_rep), schema_or_complex
            )
        return not match


TAttrRep = TypeVar("TAttrRep", bound=Union[AttrRep, BoundedAttrRep])


class AttributeOperator(abc.ABC, Generic[TSchemaOrComplex]):
    SCIM_OP = None

    def __init__(self, attr_rep: TAttrRep):
        self._attr_rep = attr_rep

    @property
    def attr_rep(self) -> TAttrRep:
        return self._attr_rep

    @abc.abstractmethod
    def match(
        self,
        value: Any,
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """Docs placeholder."""


class UnaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: set[str]
    SUPPORTED_TYPES: set[type]
    OPERATOR: Callable[[Any], bool]

    def match(
        self,
        value: Any,
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        _ensure_correct_obj(schema_or_complex, self._attr_rep)
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None:
            return False

        if attr.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return False

        if attr.multi_valued:
            if isinstance(value, list):
                match = any(
                    [self.OPERATOR(item) for item in value if type(item) in self.SUPPORTED_TYPES]
                )
            else:
                match = False
        else:
            match = self.OPERATOR(value)

        return match


def _pr_operator(value):
    if isinstance(value, dict):
        return any([_pr_operator(val) for val in value.values()])
    if isinstance(value, str):
        return value != ""
    return value not in [None, Missing]


class Present(UnaryAttributeOperator):
    SCIM_OP = "pr"
    SUPPORTED_SCIM_TYPES = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    SUPPORTED_TYPES = {str, bool, int, dict, float, type(None)}
    OPERATOR = staticmethod(_pr_operator)


T2 = TypeVar("T2")


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: set[str]
    SUPPORTED_TYPES: set[type]
    OPERATOR: Callable[[Any, Any], bool]

    def __init__(self, attr_rep: TAttrRep, value: T2):
        super().__init__(attr_rep=attr_rep)
        if type(value) not in self.SUPPORTED_TYPES:
            raise TypeError(
                f"unsupported value type {type(value).__name__!r} for {self.SCIM_OP!r} operator"
            )
        self._value = value

    @property
    def value(self) -> T2:
        return self._value

    def _get_values_for_comparison(
        self, value: Any, attr: Attribute
    ) -> Optional[list[tuple[Any, Any]]]:
        if attr.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return None

        op_value = self.value
        convert = converters.get(attr.SCIM_NAME, lambda _: _)

        if isinstance(attr, Complex):
            value_sub_attr = getattr(attr.attrs, "value", None)
            if value_sub_attr is None:
                return None

            if not attr.multi_valued:
                return None

            attr = value_sub_attr
            value = [item.get("value") for item in value]

        elif not isinstance(value, list):
            value = [value]

        if isinstance(attr, AttributeWithCaseExact):
            if isinstance(attr, String):
                try:
                    value = [
                        attr.precis.enforce(item) if isinstance(item, str) else item
                        for item in value
                    ]
                    if isinstance(op_value, str):
                        op_value = attr.precis.enforce(op_value)
                except UnicodeEncodeError:
                    return None
            if attr.case_exact:
                return [(item, op_value) for item in value]

            if isinstance(op_value, str):
                op_value = op_value.lower()
            return [(item.lower() if isinstance(item, str) else item, op_value) for item in value]

        op_value = convert(op_value)
        return [(item, op_value) for item in value]

    def match(
        self,
        value: Any,
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        _ensure_correct_obj(schema_or_complex, self._attr_rep)
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None:
            return False

        if value in [None, Missing, Invalid]:
            return False

        values = self._get_values_for_comparison(value, attr)

        if values is None:
            return False

        for attr_value, op_value in values:
            try:
                if self.OPERATOR(attr_value, op_value):
                    return True
            except (AttributeError, TypeError):
                pass

        return False


class Equal(BinaryAttributeOperator):
    SCIM_OP = "eq"
    OPERATOR = operator.eq
    SUPPORTED_SCIM_TYPES = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    SUPPORTED_TYPES = {str, bool, int, float, type(None)}


class NotEqual(BinaryAttributeOperator):
    SCIM_OP = "ne"
    OPERATOR = operator.ne
    SUPPORTED_SCIM_TYPES = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    SUPPORTED_TYPES = {str, bool, int, float, type(None)}


class Contains(BinaryAttributeOperator):
    SCIM_OP = "co"
    OPERATOR = operator.contains
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}


class StartsWith(BinaryAttributeOperator):
    @staticmethod
    def _starts_with(val1: str, val2: str):
        return val1.startswith(val2)

    SCIM_OP = "sw"
    OPERATOR = _starts_with
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}


class EndsWith(BinaryAttributeOperator):
    @staticmethod
    def _ends_with(val1: str, val2: str):
        return val1.endswith(val2)

    SCIM_OP = "ew"
    OPERATOR = _ends_with
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}


class GreaterThan(BinaryAttributeOperator):
    SCIM_OP = "gt"
    OPERATOR = operator.gt
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}


class GreaterThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "ge"
    OPERATOR = operator.ge
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}


class LesserThan(BinaryAttributeOperator):
    SCIM_OP = "lt"
    OPERATOR = operator.lt
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}


class LesserThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "le"
    OPERATOR = operator.le
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}


TComplexAttributeSubOperator = TypeVar(
    "TComplexAttributeSubOperator", bound=Union[LogicalOperator, "AttributeOperator"]
)


class ComplexAttributeOperator(Generic[TSchemaOrComplex]):
    def __init__(
        self,
        attr_rep: TAttrRep,
        sub_operator: TComplexAttributeSubOperator,
    ):
        self._attr_rep = attr_rep
        self._sub_operator = sub_operator

    @property
    def attr_rep(self) -> TAttrRep:
        return self._attr_rep

    @property
    def sub_operator(self) -> TComplexAttributeSubOperator:
        return self._sub_operator

    def match(
        self,
        value: Optional[
            Union[list[Union[SCIMDataContainer, dict[str, Any]]], SCIMDataContainer, dict[str, Any]]
        ],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        _ensure_correct_obj(schema_or_complex, self._attr_rep)
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None or not isinstance(attr, Complex):
            return False
        if (
            attr.multi_valued
            and not isinstance(value, list)
            or not attr.multi_valued
            and isinstance(value, list)
        ):
            return False

        value = value or ([] if attr.multi_valued else SCIMDataContainer())

        if not isinstance(value, list):
            value = [value]

        value = [
            SCIMDataContainer(item) for item in value if isinstance(item, (dict, SCIMDataContainer))
        ]

        if isinstance(self._sub_operator, AttributeOperator):
            for item in value:
                item_value = item.get(self._sub_operator.attr_rep)
                match = self._sub_operator.match(item_value, attr)
                if match:
                    return True
            return False

        for item in value:
            match = self._sub_operator.match(item, attr)
            if match:
                return True
        return False


def _ensure_correct_obj(schema_or_complex: TSchemaOrComplex, attr_rep: TAttrRep):
    if isinstance(schema_or_complex, BaseSchema) and not isinstance(attr_rep, BoundedAttrRep):
        raise TypeError(f"BoundedAttrRep can be handled by BaseSchema only")
    elif isinstance(schema_or_complex, Complex) and not isinstance(attr_rep, AttrRep):
        raise TypeError(f"AttrRep can be handled by Complex attribute only")
