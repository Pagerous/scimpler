import abc
import operator
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from src.parser.attributes.attributes import Attribute, ComplexAttribute
from src.parser.attributes import type as at


class LogicalOperator(abc.ABC):
    SCIM_OP = None

    @abc.abstractmethod
    def match(self, value: Dict[str, Any], attrs: [str, Attribute]) -> bool: ...


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(self, *sub_operators: Union["LogicalOperator", "AttributeOperator"]):
        self._sub_operators = sub_operators

    @property
    def sub_operators(self) -> Tuple[Union["LogicalOperator", "AttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(
        self, value: Dict[str, Any], attrs: [str, Attribute]
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, attrs)
            else:
                if sub_operator.attr_name not in attrs:
                    yield False
                else:
                    yield sub_operator.match(
                        value.get(sub_operator.attr_name),
                        attrs.get(sub_operator.attr_name),
                    )


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(self, value: Dict[str, Any], attrs: [str, Attribute]) -> bool:
        return all(self._collect_matches(value, attrs))


class Or(MultiOperandLogicalOperator):
    SCIM_OP = "or"

    def match(self, value: Dict[str, Any], attrs: [str, Attribute]) -> bool:
        return any(self._collect_matches(value, attrs))


T1 = TypeVar("T1", bound=Union[LogicalOperator, "AttributeOperator"])


class Not(LogicalOperator):
    SCIM_OP = "not"

    def __init__(self, sub_operator: T1):
        self._sub_operator = sub_operator

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(self, value: Dict[str, Any], attrs: [str, Attribute]) -> bool:
        if isinstance(self._sub_operator, LogicalOperator):
            return not self._sub_operator.match(value, attrs)
        if self._sub_operator.attr_name not in attrs:
            return False
        return not self._sub_operator.match(
            value.get(self._sub_operator.attr_name),
            attrs.get(self._sub_operator.attr_name)
        )


class AttributeOperator(abc.ABC):
    SCIM_OP = None

    def __init__(self, attr_name: str):
        self._attr_name = attr_name

    @property
    def attr_name(self) -> str:
        return self._attr_name.lower()

    @property
    def display_name(self) -> str:
        return self._attr_name

    @abc.abstractmethod
    def match(self, value: Any, attr: Attribute) -> bool: ...


class Present(AttributeOperator):
    SCIM_OP = "pr"

    def match(self, value: Any, attr: Attribute) -> bool:
        if isinstance(attr, ComplexAttribute):
            if attr.multi_valued:
                return any([item.get("value") for item in value])
            return False
        if isinstance(value, Sequence):
            return bool(value)
        return value is not None


T2 = TypeVar("T2")


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: Set[str]
    OPERATOR: Callable[[Any, Any], bool]

    def __init__(self, attr_name: str, value: T2):
        super().__init__(attr_name)
        self._value = value

    @property
    def value(self) -> T2:
        return self._value

    def get_values_for_comparison(self, value: Any, attr: Attribute) -> Optional[Tuple[Any, Any]]:
        if attr.type.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return None

        if isinstance(attr, ComplexAttribute):
            value_sub_attr = attr.sub_attributes.get("value")
            if value_sub_attr is None:
                return None

            if not isinstance(self.value, value_sub_attr.type.TYPE):
                return None

            if attr.multi_valued:
                value = [item.get("value") for item in value]
            else:
                value = value.get("value")
        else:
            if not isinstance(self.value, attr.type.TYPE):
                return None

        if attr.type.SCIM_NAME == "dateTime":
            try:
                return value, datetime.fromisoformat(self.value)
            except ValueError:
                return None

        if isinstance(self.value, str):
            if not attr.case_exact:
                if attr.multi_valued:
                    value = [item.lower() for item in value]
                else:
                    value = value.lower()
                return value, self.value.lower()
            return value, self.value

        return value, self.value

    def match(self, value: Any, attr: Attribute) -> bool:
        if self.attr_name != attr.name:
            return False

        values = self.get_values_for_comparison(value, attr)
        if values is None:
            return False

        if isinstance(values[0], (list, tuple)):
            for item in values[0]:
                if self.OPERATOR(item, values[1]):
                    return True
            return False
        return self.OPERATOR(values[0], values[1])


class Equal(BinaryAttributeOperator):
    SCIM_OP = "eq"
    OPERATOR = operator.eq
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.ExternalReference.SCIM_NAME,
        at.URIReference.SCIM_NAME,
        at.SCIMReference.SCIM_NAME,
        at.Boolean.SCIM_NAME,
        at.Binary.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class NotEqual(BinaryAttributeOperator):
    SCIM_OP = "ne"
    OPERATOR = operator.ne
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.ExternalReference.SCIM_NAME,
        at.URIReference.SCIM_NAME,
        at.SCIMReference.SCIM_NAME,
        at.Boolean.SCIM_NAME,
        at.Binary.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class Contains(BinaryAttributeOperator):
    SCIM_OP = "co"
    OPERATOR = operator.contains
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.URIReference.SCIM_NAME,
        at.SCIMReference.SCIM_NAME,
        at.ExternalReference.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class StartsWith(BinaryAttributeOperator):

    @staticmethod
    def _starts_with(val1: str, val2: str):
        return val1.startswith(val2)

    SCIM_OP = "sw"
    OPERATOR = _starts_with
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.URIReference.SCIM_NAME,
        at.SCIMReference.SCIM_NAME,
        at.ExternalReference.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class EndsWith(BinaryAttributeOperator):

    @staticmethod
    def _ends_with(val1: str, val2: str):
        return val1.endswith(val2)

    SCIM_OP = "ew"
    OPERATOR = _ends_with
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.URIReference.SCIM_NAME,
        at.SCIMReference.SCIM_NAME,
        at.ExternalReference.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class GreaterThan(BinaryAttributeOperator):
    SCIM_OP = "gt"
    OPERATOR = operator.gt
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class GreaterThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "ge"
    OPERATOR = operator.ge
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class LesserThan(BinaryAttributeOperator):
    SCIM_OP = "lt"
    OPERATOR = operator.lt
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class LesserThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "le"
    OPERATOR = operator.le
    SUPPORTED_SCIM_TYPES = {
        at.String.SCIM_NAME,
        at.DateTime.SCIM_NAME,
        at.Integer.SCIM_NAME,
        at.Decimal.SCIM_NAME,
        at.Complex.SCIM_NAME,
    }


class ComplexAttributeOperator:
    def __init__(self, attr_name: str, sub_operator: T1):
        self._attr_name = attr_name
        self._sub_operator = sub_operator

    @property
    def attr_name(self) -> str:
        return self._attr_name.lower()

    @property
    def display_name(self) -> str:
        return self._attr_name

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(self, value: Union[Sequence[Dict[str, Any]], Dict[str, Any]], attr: ComplexAttribute) -> bool:
        sub_attrs = attr.sub_attributes

        if attr.multi_valued:
            if isinstance(self._sub_operator, AttributeOperator):
                for item in value:
                    if self._sub_operator.match(
                        value=item.get(self._sub_operator.attr_name),
                        attr=sub_attrs.get(self._sub_operator.attr_name),
                    ):
                        return True
                return False

            for item in value:
                if self._sub_operator.match(item, sub_attrs):
                    return True
            return False

        if isinstance(self._sub_operator, AttributeOperator):
            if self._sub_operator.match(
                    value=value.get(self._sub_operator.attr_name),
                    attr=sub_attrs.get(self._sub_operator.attr_name),
            ):
                return True
            return False

        return self._sub_operator.match(value, sub_attrs)
