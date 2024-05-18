import abc
import operator
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

from src.attributes import (
    Attribute,
    Attributes,
    AttributeWithCaseExact,
    BoundedAttributes,
    Complex,
    String,
)
from src.container import AttrRep, BoundedAttrRep, Invalid, Missing, SCIMDataContainer
from src.registry import converters


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
        attrs: Union[Attributes, BoundedAttributes],
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
        self,
        value: SCIMDataContainer,
        attrs: Union[Attributes, BoundedAttributes],
    ) -> Generator[MatchResult, None, None]:
        for sub_operator in self.sub_operators:
            if isinstance(sub_operator, LogicalOperator):
                yield sub_operator.match(value, attrs)
            else:
                yield sub_operator.match(value.get(sub_operator.attr_rep), attrs)


class And(MultiOperandLogicalOperator):
    SCIM_OP = "and"

    def match(
        self,
        value: Optional[SCIMDataContainer],
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        value = value or SCIMDataContainer()
        missing_data = False
        for match in self._collect_matches(value, attrs):
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
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        value = value or SCIMDataContainer()
        missing_data = False
        for match in self._collect_matches(value, attrs):
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
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        value = value or SCIMDataContainer()
        if isinstance(self._sub_operator, LogicalOperator):
            match = self._sub_operator.match(value, attrs)
            if match.status == MatchStatus.MISSING_DATA:
                return MatchResult.failed()
            if match.status == MatchStatus.FAILED:
                return MatchResult.passed()
            return MatchResult.failed()
        match = self._sub_operator.match(value.get(self._sub_operator.attr_rep), attrs)
        if match.status == MatchStatus.FAILED:
            return MatchResult.passed()
        return MatchResult.failed()


TAttrRep = TypeVar("TAttrRep", bound=Union[AttrRep, BoundedAttrRep])


class AttributeOperator(abc.ABC):
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
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        ...


class UnaryAttributeOperator(AttributeOperator, abc.ABC):
    SUPPORTED_SCIM_TYPES: Set[str]
    SUPPORTED_TYPES: Set[Type]
    OPERATOR: Callable[[Any], bool]

    def match(
        self,
        value: Any,
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        _ensure_correct_attrs(attrs, self._attr_rep)
        attr = attrs.get(self._attr_rep)
        if attr is None:
            return MatchResult.failed_no_attr()

        if attr.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return MatchResult.failed()

        if attr.multi_valued:
            if isinstance(value, List):
                match = any(
                    [self.OPERATOR(item) for item in value if type(item) in self.SUPPORTED_TYPES]
                )
            else:
                match = False
        else:
            match = self.OPERATOR(value)

        return MatchResult.passed() if match else MatchResult.failed()


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
    SUPPORTED_SCIM_TYPES: Set[str]
    SUPPORTED_TYPES: Set[Type]
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
    ) -> Optional[List[Tuple[Any, Any]]]:
        if attr.SCIM_NAME not in self.SUPPORTED_SCIM_TYPES:
            return None

        op_value = self.value
        convert = converters.get(attr.SCIM_NAME, lambda _: _)

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

            attr = value_sub_attr
            value = [item.get("value") for item in value]
        elif not isinstance(value, List):
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
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        _ensure_correct_attrs(attrs, self._attr_rep)
        attr = attrs.get(self._attr_rep)
        if attr is None:
            return MatchResult.failed_no_attr()

        if value in [None, Missing]:
            return MatchResult.missing_data()
        elif value is Invalid:
            return MatchResult.failed()

        values = self._get_values_for_comparison(value, attr)

        if values is None:
            return MatchResult.failed()

        for attr_value, op_value in values:
            try:
                if self.OPERATOR(attr_value, op_value):
                    return MatchResult.passed()
            except TypeError:
                pass

        return MatchResult.failed()


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


class ComplexAttributeOperator:
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
        value: Optional[Union[List[SCIMDataContainer], SCIMDataContainer]],
        attrs: Union[Attributes, BoundedAttributes],
    ) -> MatchResult:
        _ensure_correct_attrs(attrs, self._attr_rep)
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
            for item in value:
                item_value = item.get(self._sub_operator.attr_rep)
                match = self._sub_operator.match(item_value, attr.attrs)
                if match.status == MatchStatus.PASSED:
                    return MatchResult.passed()
            return MatchResult.failed()

        for item in value:
            match = self._sub_operator.match(item, attr.attrs)
            if match.status == MatchStatus.PASSED:
                return MatchResult.passed()
        return MatchResult.failed()


def _ensure_correct_attrs(
    attrs: Union[Attributes, BoundedAttributes], attr_rep: Union[AttrRep, BoundedAttrRep]
):
    if isinstance(attrs, BoundedAttributes) and not isinstance(attr_rep, BoundedAttrRep):
        raise TypeError(f"bounded attr can be handled by BoundedAttributes only")
    elif isinstance(attrs, Attributes) and not isinstance(attr_rep, AttrRep):
        raise TypeError(f"attr can be handled by Attributes only")
