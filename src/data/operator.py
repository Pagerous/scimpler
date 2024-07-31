import abc
import operator
from typing import Any, Callable, Generator, Generic, Optional, TypeVar, Union

from src.container import AttrRep, Invalid, Missing, SCIMData
from src.data.attrs import Attribute, AttributeWithCaseExact, Complex, String
from src.data.schemas import BaseSchema

TSchemaOrComplex = TypeVar("TSchemaOrComplex", bound=Union[BaseSchema, Complex])


class Operator(abc.ABC, Generic[TSchemaOrComplex]):
    @abc.abstractmethod
    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """Docs placeholder."""


class LogicalOperator(Operator, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def op(cls) -> str:
        """Docs placeholder."""

    @property
    @abc.abstractmethod
    def sub_operators(self) -> list[Operator]:
        """Docs placeholder."""

    def _collect_matches(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            yield sub_operator.match(value, schema_or_complex)


class And(LogicalOperator):
    def __init__(self, *sub_operators: Operator):
        self._sub_operators = list(sub_operators)

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or SCIMData()
        for match in self._collect_matches(value, schema_or_complex):
            if not match:
                return False
        return True

    @classmethod
    def op(cls) -> str:
        return "and"

    @property
    def sub_operators(self) -> list[Operator]:
        return self._sub_operators


class Or(LogicalOperator):
    def __init__(self, *sub_operators: Operator):
        self._sub_operators = list(sub_operators)

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or SCIMData()
        for match in self._collect_matches(value, schema_or_complex):
            if match:
                return True
        return False

    @classmethod
    def op(cls) -> str:
        return "or"

    @property
    def sub_operators(self) -> list[Operator]:
        return self._sub_operators


class Not(LogicalOperator):
    def __init__(self, sub_operator: Operator):
        self._sub_operators = [sub_operator]

    @classmethod
    def op(cls) -> str:
        return "not"

    @property
    def sub_operators(self) -> list[Operator]:
        return self._sub_operators

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        return not next(self._collect_matches(value, schema_or_complex))


class AttributeOperator(Operator, abc.ABC):
    def __init__(self, attr_rep: AttrRep):
        self._attr_rep = attr_rep

    @classmethod
    @abc.abstractmethod
    def op(cls) -> str:
        """Docs placeholder."""

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep


class UnaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: set[str]
    SUPPORTED_TYPES: set[type]
    OPERATOR: Callable[[Any], bool]

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None:
            return False

        if attr.scim_type() not in self.SUPPORTED_SCIM_TYPES:
            return False

        if not value:
            return False

        attr_value = value.get(self.attr_rep)

        if attr.multi_valued:
            if isinstance(attr_value, list):
                match = any(
                    [
                        self.OPERATOR(item)
                        for item in attr_value
                        if type(item) in self.SUPPORTED_TYPES
                    ]
                )
            else:
                match = False
        else:
            match = self.OPERATOR(attr_value)

        return match


def _pr_operator(value):
    if isinstance(value, dict):
        return any([_pr_operator(val) for val in value.values()])
    if isinstance(value, str):
        return value != ""
    return value not in [None, Missing]


class Present(UnaryAttributeOperator):
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

    @classmethod
    def op(cls) -> str:
        return "pr"


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: set[str]
    SUPPORTED_TYPES: set[type]
    OPERATOR: Callable[[Any, Any], bool]

    def __init__(self, attr_rep: AttrRep, value: Any):
        super().__init__(attr_rep=attr_rep)
        if type(value) not in self.SUPPORTED_TYPES:
            raise TypeError(
                f"unsupported value type {type(value).__name__!r} for {self.op!r} operator"
            )
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    def _get_values_for_comparison(
        self, value: Any, attr: Attribute
    ) -> Optional[list[tuple[Any, Any]]]:
        if attr.scim_type() not in self.SUPPORTED_SCIM_TYPES:
            return None

        op_value = self.value
        if isinstance(attr, Complex):
            value_sub_attr = attr.attrs.get("value")
            if value_sub_attr is None:
                return None

            if not attr.multi_valued:
                return None

            attr = value_sub_attr
            value = [item.get("value") for item in value]

        elif not isinstance(value, list):
            value = [value]

        if isinstance(op_value, attr.base_types()):
            op_value = attr.deserialize(op_value)

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
        return [(item, op_value) for item in value]

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None:
            return False

        attr_value = None if not value else value.get(self._attr_rep)

        if attr_value in [None, Missing, Invalid]:
            return False

        values = self._get_values_for_comparison(attr_value, attr)

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

    @classmethod
    def op(cls) -> str:
        return "eq"


class NotEqual(BinaryAttributeOperator):
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

    @classmethod
    def op(cls) -> str:
        return "ne"


class Contains(BinaryAttributeOperator):
    OPERATOR = operator.contains
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}

    @classmethod
    def op(cls) -> str:
        return "co"


class StartsWith(BinaryAttributeOperator):
    @staticmethod
    def _starts_with(val1: str, val2: str):
        return val1.startswith(val2)

    OPERATOR = _starts_with
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}

    @classmethod
    def op(cls) -> str:
        return "sw"


class EndsWith(BinaryAttributeOperator):
    @staticmethod
    def _ends_with(val1: str, val2: str):
        return val1.endswith(val2)

    OPERATOR = _ends_with
    SUPPORTED_SCIM_TYPES = {"string", "reference", "complex"}
    SUPPORTED_TYPES = {str, float}

    @classmethod
    def op(cls) -> str:
        return "ew"


class GreaterThan(BinaryAttributeOperator):
    OPERATOR = operator.gt
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "gt"


class GreaterThanOrEqual(BinaryAttributeOperator):
    OPERATOR = operator.ge
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "ge"


class LesserThan(BinaryAttributeOperator):
    OPERATOR = operator.lt
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "lt"


class LesserThanOrEqual(BinaryAttributeOperator):
    OPERATOR = operator.le
    SUPPORTED_SCIM_TYPES = {"string", "dateTime", "integer", "decimal", "complex"}
    SUPPORTED_TYPES = {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "le"


TComplexAttributeSubOperator = TypeVar(
    "TComplexAttributeSubOperator", bound=Union[LogicalOperator, "AttributeOperator"]
)


class ComplexAttributeOperator(Operator, Generic[TComplexAttributeSubOperator]):
    def __init__(
        self,
        attr_rep: AttrRep,
        sub_operator: TComplexAttributeSubOperator,
    ):
        self._attr_rep = attr_rep
        self._sub_operator = sub_operator

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep

    @property
    def sub_operator(self) -> TComplexAttributeSubOperator:
        return self._sub_operator

    def match(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        attr = schema_or_complex.attrs.get(self._attr_rep)
        if attr is None or not value or not isinstance(attr, Complex):
            return False

        attr_value = value.get(self._attr_rep)
        if (
            attr.multi_valued
            and not isinstance(attr_value, list)
            or not attr.multi_valued
            and isinstance(attr_value, list)
        ):
            return False

        normalized = self._normalize(attr, attr_value)
        for item in normalized:
            match = self._sub_operator.match(item, attr)
            if match:
                return True
        return False

    @staticmethod
    def _normalize(attr: Complex, value: Any) -> list[SCIMData]:
        value = value or ([] if attr.multi_valued else SCIMData())
        return [
            SCIMData(item)
            for item in (value if isinstance(value, list) else [value])
            if isinstance(item, (dict, SCIMData))
        ]
