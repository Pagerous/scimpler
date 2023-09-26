import abc
from typing import Any, Generator, Tuple, TypeVar, Union


class LogicalOperator(abc.ABC):
    SCIM_OP = None

    @abc.abstractmethod
    def match(self, value: dict) -> bool: ...


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(self, *sub_operators: Union["LogicalOperator", "AttributeOperator"]):
        self._sub_operators = sub_operators

    @property
    def sub_operators(self) -> Tuple[Union["LogicalOperator", "AttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(self, value: dict) -> Generator[bool, None, None]:
        return (
            sub_operator.match(value)
            if isinstance(sub_operator, LogicalOperator)
            else sub_operator.match(value.get(sub_operator.attr_name))
            for sub_operator in self.sub_operators
        )


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(self, value: dict) -> bool:
        return all(self._collect_matches(value))


class Or(MultiOperandLogicalOperator):
    SCIM_OP = "or"

    def match(self, value: dict) -> bool:
        return any(self._collect_matches(value))


T1 = TypeVar("T1", bound=Union[LogicalOperator, "AttributeOperator"])


class Not(LogicalOperator):
    SCIM_OP = "not"

    def __init__(self, sub_operator: T1):
        self._sub_operator = sub_operator

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(self, value: Union[dict, Any]) -> bool:
        if not isinstance(value, dict):
            if isinstance(self._sub_operator, LogicalOperator):
                raise ...  # TODO: specify exact exception
            return self._sub_operator.match(value)
        if isinstance(self._sub_operator, LogicalOperator):
            return self._sub_operator.match(value)
        return self._sub_operator.match(value.get(self._sub_operator.attr_name))


class AttributeOperator(abc.ABC):
    SCIM_OP = None

    def __init__(self, attr_name: str):
        self._attr_name = attr_name

    @property
    def attr_name(self) -> str:
        return self._attr_name

    @abc.abstractmethod
    def match(self, other: Any) -> bool: ...


class Present(AttributeOperator):
    SCIM_OP = "pr"

    def match(self, other: Any) -> bool:
        if isinstance(other, (list, tuple)):
            return bool(other)
        if isinstance(other, str):
            return other != ""
        if isinstance(other, dict):
            return bool(bool(other) and any(other.values()))
        return other is not None


T2 = TypeVar("T2")


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    def __init__(self, attr_name: str, value: T2):
        super().__init__(attr_name)
        self._value = value

    @property
    def value(self) -> T2:
        return self._value


class Equal(BinaryAttributeOperator):
    SCIM_OP = "eq"

    def match(self, other: Any) -> bool:
        return other == self.value


class NotEqual(BinaryAttributeOperator):
    SCIM_OP = "ne"

    def match(self, other: Any) -> bool:
        return other != self.value


class Contains(BinaryAttributeOperator):
    SCIM_OP = "co"

    def match(self, other: str) -> bool:
        return other in self.value


class StartsWith(BinaryAttributeOperator):
    SCIM_OP = "sw"

    def match(self, other: str) -> bool:
        return other.startswith(self.value)


class EndsWith(BinaryAttributeOperator):
    SCIM_OP = "ew"

    def match(self, other: str) -> bool:
        return other.endswith(self.value)


class GreaterThan(BinaryAttributeOperator):
    SCIM_OP = "gt"

    def match(self, other: Any) -> bool:
        return other > self.value


class GreaterThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "ge"

    def match(self, other: Any) -> bool:
        return other >= self.value


class LesserThan(BinaryAttributeOperator):
    SCIM_OP = "lt"

    def match(self, other: Any) -> bool:
        return other < self.value


class LesserThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "le"

    def match(self, other: Any) -> bool:
        return other <= self.value


class ComplexAttributeOperator:
    def __init__(self, attr_name: str, sub_operator: T1):
        self._attr_name = attr_name
        self._sub_operator = sub_operator

    @property
    def attr_name(self) -> str:
        return self._attr_name

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(self, value: dict):
        if isinstance(self._sub_operator, AttributeOperator):
            return self._sub_operator.match(value.get(self._sub_operator.attr_name))
        return self._sub_operator.match(value)
