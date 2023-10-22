import abc
import operator
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from src.parser.attributes import type as at
from src.parser.attributes.attributes import Attribute, ComplexAttribute


class MatchStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    MISSING_DATA = "MISSING_DATA"


class MatchResult:
    def __init__(self, status: MatchStatus):
        self._status = status

    @classmethod
    def passed(cls):
        return cls(MatchStatus.PASSED)

    @classmethod
    def failed(cls):
        return cls(MatchStatus.FAILED)

    @classmethod
    def missing_data(cls):
        return cls(MatchStatus.MISSING_DATA)

    @property
    def status(self) -> MatchStatus:
        return self._status

    def __eq__(self, other):
        if isinstance(other, bool):
            if self._status == MatchStatus.PASSED and other is True:
                return True
            elif self._status == MatchStatus.FAILED and other is False:
                return True
            return False
        if isinstance(other, MatchResult):
            return self.status == other.status
        return False

    def __bool__(self):
        if self._status == MatchStatus.PASSED:
            return True
        elif self._status == MatchStatus.FAILED:
            return False
        raise ValueError("unable to determine result for missing data")


class LogicalOperator(abc.ABC):
    SCIM_OP = None

    @abc.abstractmethod
    def match(
        self,
        value: Dict[str, Any],
        attrs: Optional[Dict[str, Attribute]],
        strict: bool = True,
    ) -> MatchResult:
        ...


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(self, *sub_operators: Union["LogicalOperator", "AttributeOperator"]):
        self._sub_operators = sub_operators

    @property
    def sub_operators(self) -> Tuple[Union["LogicalOperator", "AttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(
        self,
        value: Dict[str, Any],
        attrs: Optional[Dict[str, Attribute]],
        strict: bool = True,
    ) -> Generator[MatchResult, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, attrs, strict)
            elif sub_operator.attr_name not in value:
                if attrs is None or sub_operator.attr_name in attrs:
                    if strict:
                        yield MatchResult.missing_data()
                    else:
                        yield MatchResult.passed()
                else:
                    yield MatchResult.failed()
            elif attrs is not None and sub_operator.attr_name not in attrs:
                yield MatchResult.failed()
            else:
                yield sub_operator.match(
                    value=value.get(sub_operator.attr_name),
                    attr=(attrs or {}).get(sub_operator.attr_name),
                )


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(
        self,
        value: Dict[str, Any],
        attrs: Optional[Dict[str, Attribute]],
        strict: bool = True,
    ) -> MatchResult:
        missing_data = False
        for match in self._collect_matches(value, attrs, strict):
            if match.status == MatchStatus.FAILED:
                return MatchResult.failed()
            if match.status == MatchStatus.MISSING_DATA:
                missing_data = True
        if missing_data:
            return MatchResult.missing_data()
        return MatchResult.passed()


class Or(MultiOperandLogicalOperator):
    SCIM_OP = "or"

    def match(
        self,
        value: Dict[str, Any],
        attrs: Optional[Dict[str, Attribute]],
        strict: bool = True,
    ) -> MatchResult:
        missing_data = False
        for match in self._collect_matches(value, attrs, strict):
            if match.status == MatchStatus.PASSED:
                return MatchResult.passed()
            if match.status == MatchStatus.MISSING_DATA:
                missing_data = True
        if missing_data:
            return MatchResult.missing_data()
        return MatchResult.failed()


T1 = TypeVar("T1", bound=Union[LogicalOperator, "AttributeOperator"])


class Not(LogicalOperator):
    SCIM_OP = "not"

    def __init__(self, sub_operator: T1):
        self._sub_operator = sub_operator

    @property
    def sub_operator(self) -> T1:
        return self._sub_operator

    def match(
        self,
        value: Dict[str, Any],
        attrs: Optional[Dict[str, Attribute]],
        strict: bool = True,
    ) -> MatchResult:
        if isinstance(self._sub_operator, LogicalOperator):
            match = self._sub_operator.match(value, attrs, strict=True)
            if match.status == MatchStatus.MISSING_DATA:
                if strict:
                    return MatchResult.failed()
                return MatchResult.passed()
            if match.status == MatchStatus.FAILED:
                return MatchResult.passed()
            return MatchResult.failed()

        if self._sub_operator.attr_name not in value:
            if (attrs is None or self._sub_operator.attr_name in attrs) and not strict:
                return MatchResult.passed()
            return MatchResult.failed()

        if attrs is not None and self._sub_operator.attr_name not in attrs:
            return MatchResult.failed()

        match = self._sub_operator.match(
            value=value.get(self._sub_operator.attr_name),
            attr=(attrs or {}).get(self._sub_operator.attr_name),
        )
        if match.status == MatchStatus.FAILED:
            return MatchResult.passed()
        return MatchResult.failed()


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
    def match(self, value: Any, attr: Optional[Attribute]) -> MatchResult:
        ...


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

    def match(self, value: Any, attr: Optional[Attribute]) -> MatchResult:
        match = False
        if attr is None:
            match = self._match_no_attr(value)
        elif isinstance(attr, ComplexAttribute):
            if isinstance(value, List):
                match = any([item.get("value") for item in value])
        elif isinstance(value, List):
            match = any([bool(item) for item in value])
        elif isinstance(value, str):
            match = bool(value)
        else:
            match = value is not None
        return MatchResult.passed() if match else MatchResult.failed()


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
                return [(datetime.fromisoformat(item), op_value) for item in value]
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

    def match(self, value: Any, attr: Optional[Attribute]) -> MatchResult:
        values = (
            self._get_values_for_comparison_no_attribute(value)
            if attr is None
            else self._get_values_for_comparison(value, attr)
        )

        if values is None:
            return MatchResult.failed()

        for attr_value, op_value in values:
            if self.OPERATOR(attr_value, op_value):
                return MatchResult.passed()
        return MatchResult.failed()


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

    def match(
        self,
        value: Union[List[Dict[str, Any]], Dict[str, Any]],
        attr: Optional[ComplexAttribute],
        strict: bool = True,
    ) -> MatchResult:
        sub_attrs = attr.sub_attributes if attr else None
        if not isinstance(value, List):
            value = [value]

        if isinstance(self._sub_operator, AttributeOperator):
            has_value = False
            for item in value:
                if self._sub_operator.attr_name not in item:
                    continue
                if sub_attrs is None or self._sub_operator.attr_name in sub_attrs:
                    has_value = True
                    if (
                        self._sub_operator.match(
                            value=item.get(self._sub_operator.attr_name),
                            attr=(sub_attrs or {}).get(self._sub_operator.attr_name),
                        ).status
                        == MatchStatus.PASSED
                    ):
                        return MatchResult.passed()
            if not has_value and not strict:
                return MatchResult.passed()
            return MatchResult.failed()

        missing_data = False
        for item in value:
            match = self._sub_operator.match(item, sub_attrs, strict)
            if match.status == MatchStatus.PASSED:
                return MatchResult.passed()
            if match.status == MatchStatus.MISSING_DATA:
                missing_data = True

        if missing_data and not strict:
            return MatchResult.passed()
        return MatchResult.failed()
