import abc
import operator
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from src.data.attributes import (
    Attribute,
    Attributes,
    Binary,
    Boolean,
    Complex,
    DateTime,
    Decimal,
    ExternalReference,
    Integer,
    SCIMReference,
    String,
    URIReference,
)
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer


class MatchStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    FAILED_NO_ATTR = "FAILED_NO_ATTR"
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
    def failed_no_attr(cls):
        return cls(MatchStatus.FAILED_NO_ATTR)

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
            elif (
                self._status in [MatchStatus.FAILED, MatchStatus.FAILED_NO_ATTR] and other is False
            ):
                return True
            return False
        if isinstance(other, MatchResult):
            return self.status == other.status
        return False

    def __bool__(self):
        if self._status == MatchStatus.PASSED:
            return True
        elif self._status in [MatchStatus.FAILED, MatchStatus.FAILED_NO_ATTR]:
            return False
        raise ValueError("unable to determine result for missing data")


class LogicalOperator(abc.ABC):
    SCIM_OP = None

    @abc.abstractmethod
    def match(
        self,
        value: Optional[SCIMDataContainer],
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        ...


class MultiOperandLogicalOperator(LogicalOperator, abc.ABC):
    def __init__(
        self,
        *sub_operators: Union["LogicalOperator", "AttributeOperator", "ComplexAttributeOperator"],
    ):
        self._sub_operators = list(sub_operators)

    @property
    def sub_operators(
        self,
    ) -> List[Union["LogicalOperator", "AttributeOperator", "ComplexAttributeOperator"]]:
        return self._sub_operators

    def _collect_matches(
        self, value: SCIMDataContainer, attrs: Attributes, strict: bool = True
    ) -> Generator[MatchResult, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, attrs, strict)
            else:
                yield sub_operator.match(value.get(sub_operator.attr_rep), attrs, strict)


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(
        self,
        value: Optional[SCIMDataContainer],
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        value = value or {}
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
        value: Optional[SCIMDataContainer],
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        value = value or {}
        missing_data = False
        for match in self._collect_matches(value, attrs, strict):
            if match.status == MatchStatus.PASSED:
                return MatchResult.passed()
            if match.status == MatchStatus.MISSING_DATA:
                missing_data = True
        if missing_data:
            return MatchResult.missing_data()
        return MatchResult.failed()


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
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        value = value or {}
        if isinstance(self._sub_operator, LogicalOperator):
            match = self._sub_operator.match(value, attrs, strict=True)
            if match.status == MatchStatus.MISSING_DATA:
                if strict:
                    return MatchResult.failed()
                return MatchResult.passed()
            if match.status == MatchStatus.FAILED:
                return MatchResult.passed()
            return MatchResult.failed()
        match = self._sub_operator.match(value.get(self._sub_operator.attr_rep), attrs, strict=True)
        if (
            match.status == MatchStatus.FAILED
            or not strict
            and match.status == MatchStatus.MISSING_DATA
        ):
            return MatchResult.passed()
        return MatchResult.failed()


class AttributeOperator(abc.ABC):
    SCIM_OP = None

    def __init__(self, attr_rep: AttrRep):
        self._attr_rep = attr_rep

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep

    @abc.abstractmethod
    def match(
        self,
        value: Any,
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        ...


class Present(AttributeOperator):
    SCIM_OP = "pr"

    def match(
        self,
        value: Any,
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        attr = attrs.get(self._attr_rep)
        if attr is None:
            return MatchResult.failed_no_attr()

        if isinstance(attr, Complex):
            if isinstance(value, List):
                match = any([item.get("value") for item in value])
            else:
                match = False
        elif isinstance(value, List):
            match = any([bool(item) for item in value])
        elif isinstance(value, str):
            match = bool(value)
        else:
            match = value not in [None, Missing, Invalid]
        return MatchResult.passed() if match else MatchResult.failed()


T2 = TypeVar("T2")


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: Set[str]
    SUPPORTED_TYPES: Set[Type]
    OPERATOR: Callable[[Any, Any], bool]

    def __init__(self, attr_rep: AttrRep, value: T2):
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
    ) -> Optional[List[Tuple[Any, Any]]]:
        if attr.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return None

        if isinstance(attr, Complex):
            value_sub_attr = None
            for sub_attr in attr.attrs:
                if sub_attr.rep.attr == "value":
                    value_sub_attr = sub_attr
                    break
            if value_sub_attr is None:
                return None

            if not attr.multi_valued:
                return None

            value = [item.get("value") for item in value]

        if attr.SCIM_NAME == "dateTime":
            try:
                return [(datetime.fromisoformat(value), datetime.fromisoformat(self.value))]
            except ValueError:
                return None

        if isinstance(attr, String):
            if not attr.case_exact:
                op_value = self.value.lower()
                if not isinstance(value, List):
                    value = [value]
                return [(item.lower(), op_value) for item in value if isinstance(item, str)]

        if not isinstance(value, List):
            value = [value]

        return [(item, self.value) for item in value]

    def match(
        self,
        value: Any,
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        attr = attrs.get(self._attr_rep)
        if attr is None:
            return MatchResult.failed_no_attr()

        if value in [None, Missing]:
            if not strict:
                return MatchResult.passed()
            return MatchResult.missing_data()
        elif value is Invalid:
            return MatchResult.failed()

        values = self._get_values_for_comparison(value, attr)

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
        String.SCIM_NAME,
        Decimal.SCIM_NAME,
        DateTime.SCIM_NAME,
        ExternalReference.SCIM_NAME,
        URIReference.SCIM_NAME,
        SCIMReference.SCIM_NAME,
        Boolean.SCIM_NAME,
        Binary.SCIM_NAME,
        Integer.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, bool, int, dict, float, type(None)}


class NotEqual(BinaryAttributeOperator):
    SCIM_OP = "ne"
    OPERATOR = operator.ne
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        Decimal.SCIM_NAME,
        DateTime.SCIM_NAME,
        ExternalReference.SCIM_NAME,
        URIReference.SCIM_NAME,
        SCIMReference.SCIM_NAME,
        Boolean.SCIM_NAME,
        Binary.SCIM_NAME,
        Integer.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, bool, int, dict, float, type(None)}


class Contains(BinaryAttributeOperator):
    SCIM_OP = "co"
    OPERATOR = operator.contains
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        URIReference.SCIM_NAME,
        SCIMReference.SCIM_NAME,
        ExternalReference.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float}


class StartsWith(BinaryAttributeOperator):
    @staticmethod
    def _starts_with(val1: str, val2: str):
        return val1.startswith(val2)

    SCIM_OP = "sw"
    OPERATOR = _starts_with
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        URIReference.SCIM_NAME,
        SCIMReference.SCIM_NAME,
        ExternalReference.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float}


class EndsWith(BinaryAttributeOperator):
    @staticmethod
    def _ends_with(val1: str, val2: str):
        return val1.endswith(val2)

    SCIM_OP = "ew"
    OPERATOR = _ends_with
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        URIReference.SCIM_NAME,
        SCIMReference.SCIM_NAME,
        ExternalReference.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float}


class GreaterThan(BinaryAttributeOperator):
    SCIM_OP = "gt"
    OPERATOR = operator.gt
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        DateTime.SCIM_NAME,
        Integer.SCIM_NAME,
        Decimal.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float, int, dict}


class GreaterThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "ge"
    OPERATOR = operator.ge
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        DateTime.SCIM_NAME,
        Integer.SCIM_NAME,
        Decimal.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float, int, dict}


class LesserThan(BinaryAttributeOperator):
    SCIM_OP = "lt"
    OPERATOR = operator.lt
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        DateTime.SCIM_NAME,
        Integer.SCIM_NAME,
        Decimal.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float, int, dict}


class LesserThanOrEqual(BinaryAttributeOperator):
    SCIM_OP = "le"
    OPERATOR = operator.le
    SUPPORTED_SCIM_TYPES = {
        String.SCIM_NAME,
        DateTime.SCIM_NAME,
        Integer.SCIM_NAME,
        Decimal.SCIM_NAME,
        Complex.SCIM_NAME,
    }
    SUPPORTED_TYPES = {str, float, int, dict}


TComplexAttributeSubOperator = TypeVar(
    "TComplexAttributeSubOperator", bound=Union[LogicalOperator, "AttributeOperator"]
)


class ComplexAttributeOperator:
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
        value: Optional[Union[List[SCIMDataContainer], SCIMDataContainer]],
        attrs: Attributes,
        strict: bool = True,
    ) -> MatchResult:
        attr = attrs.get(self._attr_rep)
        if attr is None or not isinstance(attr, Complex):
            return MatchResult.failed_no_attr()
        if (
            attr.multi_valued
            and not isinstance(value, List)
            or not attr.multi_valued
            and isinstance(value, List)
        ):
            return MatchResult.failed()

        value = value or ([] if attr.multi_valued else SCIMDataContainer())

        if not isinstance(value, List):
            value = [value]

        if isinstance(self._sub_operator, AttributeOperator):
            has_value = False
            for item in value:
                item_value = item.get(self._sub_operator.attr_rep)
                if item_value not in [None, Missing]:
                    has_value = True
                match = self._sub_operator.match(item_value, attr.attrs, strict)
                if match.status == MatchStatus.PASSED:
                    return MatchResult.passed()
            if not has_value and not strict:
                return MatchResult.passed()
            return MatchResult.failed()

        missing_data = False
        for item in value:
            match = self._sub_operator.match(item, attr.attrs, strict)
            if match.status == MatchStatus.PASSED:
                return MatchResult.passed()
            if match.status == MatchStatus.MISSING_DATA:
                missing_data = True

        if missing_data and not strict:
            return MatchResult.passed()
        return MatchResult.failed()
