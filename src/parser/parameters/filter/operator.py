import abc
import operator
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Optional,
    List,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from src.parser.attributes.attributes import Attribute, ComplexAttribute
from src.parser.attributes import type as at


class LogicalOperator(abc.ABC):
    SCIM_OP = None

    @abc.abstractmethod
    def match(self, value: Dict[str, Any], attrs: Optional[Dict[str, Attribute]]) -> bool: ...


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(self, *sub_operators: Union["LogicalOperator", "AttributeOperator"]):
        self._sub_operators = sub_operators

    @property
    def sub_operators(self) -> Tuple[Union["LogicalOperator", "AttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(
        self, value: Dict[str, Any], attrs: Optional[Dict[str, Attribute]]
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, attrs)
            elif attrs is not None and sub_operator.attr_name not in attrs:
                yield False
            else:
                yield sub_operator.match(
                    value=value.get(sub_operator.attr_name),
                    attr=(attrs or {}).get(sub_operator.attr_name),
                )


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(self, value: Dict[str, Any], attrs: Optional[Dict[str, Attribute]]) -> bool:
        return all(self._collect_matches(value, attrs))


class Or(MultiOperandLogicalOperator):
    SCIM_OP = "or"

    def match(self, value: Dict[str, Any], attrs: Optional[Dict[str, Attribute]]) -> bool:
        return any(self._collect_matches(value, attrs))


T1 = TypeVar("T1", bound=Union[LogicalOperator, "AttributeOperator"])


class Not(LogicalOperator):
    SCIM_OP = "not"

    def __init__(self, sub_operator: T1):
        self._sub_operator = sub_operator

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(self, value: Dict[str, Any], attrs: Optional[Dict[str, Attribute]]) -> bool:
        if isinstance(self._sub_operator, LogicalOperator):
            return not self._sub_operator.match(value, attrs)

        if attrs is not None and self._sub_operator.attr_name not in attrs:
            return False

        return not self._sub_operator.match(
            value=value.get(self._sub_operator.attr_name),
            attr=(attrs or {}).get(self._sub_operator.attr_name)
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
    def match(self, value: Any, attr: Optional[Attribute]) -> bool: ...


class Present(AttributeOperator):
    SCIM_OP = "pr"

    @staticmethod
    def _match_no_attr(value: Any) -> bool:
        if isinstance(value, List):
            for item in value:
                if isinstance(item, dict):
                    if bool(item.get("value")):
                        return True
                elif bool(item):
                    return True
            return False
        if isinstance(value, Dict):
            return False
        if isinstance(value, str):
            return bool(value)
        return value is not None

    def match(self, value: Any, attr: Optional[Attribute]) -> bool:
        if attr is None:
            return self._match_no_attr(value)
        if isinstance(attr, ComplexAttribute):
            if isinstance(value, List):
                return any([item.get("value") for item in value])
            return False
        if isinstance(value, List):
            return any([bool(item) for item in value])
        if isinstance(value, str):
            return bool(value)
        return value is not None


T2 = TypeVar("T2")


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: Set[str]
    SUPPORTED_TYPES: Set[Type]
    OPERATOR: Callable[[Any, Any], bool]

    def __init__(self, attr_name: str, value: T2):
        super().__init__(attr_name)
        if type(value) not in self.SUPPORTED_TYPES:
            raise TypeError(
                f"unsupported value type {type(value).__name__!r} for {self.SCIM_OP!r} operator"
            )
        self._value = value

    @property
    def value(self) -> T2:
        return self._value

    def _get_values_for_comparison_no_attribute(
            self, value: Any
    ) -> Optional[List[Tuple[Any, Any]]]:
        if not isinstance(value, List):
            value = [value]

        value_ = []
        for item in value:
            if isinstance(item, Dict):
                item_value = item.get("value")
                if item_value is not None and isinstance(item_value, type(self.value)):
                    value_.append(item_value)
            elif not isinstance(item, type(self.value)):
                return None
            else:
                value_.append(item)
        value = value_

        if isinstance(self.value, str):
            try:
                op_value = datetime.fromisoformat(self.value)
                return [
                    (datetime.fromisoformat(item), op_value)
                    for item in value
                ]
            except ValueError:
                value_ = []
                for item in value:
                    value_.extend([(item.lower(), self.value.lower()), (item, self.value)])
                return value_

        return [(item, self.value) for item in value]

    def _get_values_for_comparison(
        self, value: Any, attr: Attribute
    ) -> Optional[List[Tuple[Any, Any]]]:
        if attr.type.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return None

        if isinstance(attr, ComplexAttribute):
            value_sub_attr = attr.sub_attributes.get("value")
            if value_sub_attr is None:
                return None

            if not isinstance(self.value, value_sub_attr.type.TYPE):
                return None

            if not attr.multi_valued:
                return None

            value = [item.get("value") for item in value]

        else:
            if not isinstance(self.value, attr.type.TYPE):
                return None

        if attr.type.SCIM_NAME == "dateTime":
            try:
                return [(datetime.fromisoformat(value), datetime.fromisoformat(self.value))]
            except ValueError:
                return None

        if isinstance(self.value, str):
            if not attr.case_exact:
                op_value = self.value.lower()
                if not isinstance(value, List):
                    value = [value]
                return [(item.lower(), op_value) for item in value]

        if not isinstance(value, List):
            value = [value]

        return [(item, self.value) for item in value]

    def match(self, value: Any, attr: Optional[Attribute]) -> bool:
        if attr is not None:
            if self.attr_name != attr.name:
                return False
            values = self._get_values_for_comparison(value, attr)
        else:
            values = self._get_values_for_comparison_no_attribute(value)

        if values is None:
            return False

        for attr_value, op_value in values:
            if self.OPERATOR(attr_value, op_value):
                return True
        return False


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
    SUPPORTED_TYPES = {str, bool, int, dict, float, type(None)}


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
    SUPPORTED_TYPES = {str, bool, int, dict, float, type(None)}


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
    SUPPORTED_TYPES = {str, float}


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
    SUPPORTED_TYPES = {str, float}


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
    SUPPORTED_TYPES = {str, float}


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
    SUPPORTED_TYPES = {str, float, int, dict}


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
    SUPPORTED_TYPES = {str, float, int, dict}


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
    SUPPORTED_TYPES = {str, float, int, dict}


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
    SUPPORTED_TYPES = {str, float, int, dict}


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

    def match(self, value: Union[List[Dict[str, Any]], Dict[str, Any]], attr: Optional[ComplexAttribute]) -> bool:
        sub_attrs = attr.sub_attributes if attr else None
        if not isinstance(value, List):
            value = [value]

        if isinstance(self._sub_operator, AttributeOperator):
            for item in value:
                if self._sub_operator.match(
                    value=item.get(self._sub_operator.attr_name),
                    attr=(sub_attrs or {}).get(self._sub_operator.attr_name),
                ):
                    return True
            return False

        for item in value:
            if self._sub_operator.match(item, sub_attrs):
                return True
        return False
