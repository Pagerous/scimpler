import abc
import inspect
import operator
from abc import ABC
from typing import Any, Generator, Generic, Mapping, Optional, TypeVar, Union, final

from typing_extensions import override

from scimpler._registry import register_binary_operator, register_unary_operator
from scimpler.data.attrs import Attribute, AttributeWithCaseExact, Complex, String
from scimpler.data.identifiers import AttrRep
from scimpler.data.schemas import ResourceSchema
from scimpler.data.scim_data import Invalid, Missing, ScimData

TSchemaOrComplex = TypeVar("TSchemaOrComplex", bound=Union[ResourceSchema, Complex])


class Operator(abc.ABC, Generic[TSchemaOrComplex]):
    """
    Base class for operators.
    """

    @abc.abstractmethod
    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """
        Tests a given `value` against the operator and returns `True`
        if it matches, `False` otherwise.

        Args:
            value: The value to test.
            schema_or_complex: Schema or `Complex` attribute that describes the value.

        Returns:
            Flag indicating whether the value matches the operator.
        """


class LogicalOperator(Operator, abc.ABC):
    """
    Base class for logical operators.
    """

    op: str

    def __init__(self, *sub_operators: Operator):
        """
        Args:
            *sub_operators: Sub-operators which are evaluated separately.
        """
        self._sub_operators = list(sub_operators)

    @property
    def sub_operators(self) -> list[Operator]:
        """Sub-operators contained inside the operator."""
        return self._sub_operators

    def _collect_matches(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            yield sub_operator.match(value, schema_or_complex)


@final
class And(LogicalOperator):
    """
    Represents `and` SCIM operator. Matches if all sub-operators match.
    """

    op: str = "and"

    @override
    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or ScimData()
        for match in self._collect_matches(value, schema_or_complex):
            if not match:
                return False
        return True


@final
class Or(LogicalOperator):
    """
    Represents `or` SCIM operator. Matches if any of sub-operators match.
    """

    op: str = "or"

    @override
    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        value = value or ScimData()
        for match in self._collect_matches(value, schema_or_complex):
            if match:
                return True
        return False


@final
class Not(LogicalOperator):
    """
    Represents `not` SCIM operator. Matches if a sub-operator does not match.
    """

    op = "not"

    def __init__(self, sub_operator: Operator):
        super().__init__(sub_operator)

    @override
    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        return not next(self._collect_matches(value, schema_or_complex))


class AttributeOperatorMeta(abc.ABCMeta):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not inspect.isabstract(cls):
            if issubclass(cls, UnaryAttributeOperator):
                register_unary_operator(cls)
            elif issubclass(cls, BinaryAttributeOperator):
                register_binary_operator(cls)
            else:
                raise TypeError("custom subclassing of 'AttributeOperator' is forbidden")


class AttributeOperator(Operator, ABC, metaclass=AttributeOperatorMeta):
    """
    Base class for all operators that involve attributes directly.
    Every subclass which is not an abstract must specify `op`,
    `supported_scim_types`, and `supported_types` class attributes.
    """

    op: str
    supported_scim_types: set[str]
    supported_types: set[type]

    def __init__(self, attr_rep: AttrRep):
        """
        Args:
            attr_rep: The representation of an attribute which value should be matched.
        """
        self._attr_rep = attr_rep

    @property
    def attr_rep(self) -> AttrRep:
        """
        The representation of an attribute which value should be matched.
        """
        return self._attr_rep

    @classmethod
    def is_type_supported(cls, value):
        return type(value) in cls.supported_types


class UnaryAttributeOperator(AttributeOperator, abc.ABC):
    """
    Base class for all unary operators. Every subclass which is not an abstract must specify `op`,
    `supported_scim_types`, and `supported_types` class attributes.
    """

    @staticmethod
    @abc.abstractmethod
    def operator(value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """

    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """
        Tests a given `value` against the operator and returns `True`
        if it matches, `False` otherwise. If the `value` belongs to multi-valued
        attribute, the whole `value` matches if one of its items matches.

        Args:
            value: The value to test.
            schema_or_complex: Schema or `Complex` attribute that describes the value.

        Returns:
            Flag indicating whether the value matches the operator.
        """
        attr = schema_or_complex.attrs.get(self.attr_rep)
        if attr is None:
            return False

        if attr.scim_type not in self.supported_scim_types:
            return False

        if not value:
            return False

        attr_value = value.get(self.attr_rep)

        if attr.multi_valued:
            if isinstance(attr_value, list):
                match = any(
                    [self.operator(item) for item in attr_value if self.is_type_supported(item)]
                )
            else:
                match = False
        else:
            match = self.operator(attr_value)

        return match


@final
class Present(UnaryAttributeOperator):
    op = "pr"
    supported_scim_types = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    supported_types = {str, bool, int, ScimData, float, type(None)}

    @staticmethod
    def operator(value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        if isinstance(value, Mapping):
            return any([Present.operator(val) for val in value.values()])
        if isinstance(value, str):
            return value != ""
        return value not in [None, Missing]


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    """
    Base class for all binary operators. Every subclass which is not an abstract must specify `op`,
    `supported_scim_types`, and `supported_types` class attributes.
    """

    def __init__(self, attr_rep: AttrRep, value: Any):
        """
        Args:
            attr_rep: A representation of an attribute which value should be
                compared with the operator's value.
            value: The operator's value (right operand), compared to the attribute's value
                (left operand).
        """
        super().__init__(attr_rep=attr_rep)
        if not self.is_type_supported(value):
            raise TypeError(
                f"value type {type(value).__name__!r} is not supported by {self.op!r} operator"
            )
        self._value = value

    @property
    def value(self) -> Any:
        """
        The operator's value (right operand), compared to the attribute's value (left operand).
        """
        return self._value

    @staticmethod
    @abc.abstractmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """

    def _get_values(self, value: Any, attr: Attribute) -> Optional[list[tuple[Any, Any]]]:
        if attr.scim_type not in self.supported_scim_types:
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

        if isinstance(op_value, attr.base_types):
            op_value = attr.deserialize(op_value)

        if not isinstance(attr, AttributeWithCaseExact):
            return [(item, op_value) for item in value]

        return self._get_values_for_attr_with_case_exact(
            attr=attr,
            op_value=op_value,
            attr_value=value,
        )

    @staticmethod
    def _get_values_for_attr_with_case_exact(
        attr: AttributeWithCaseExact, op_value: Any, attr_value: list[Any]
    ) -> Optional[list[tuple[Any, Any]]]:
        if isinstance(attr, String):
            try:
                attr_value = [
                    attr.precis.enforce(item) if isinstance(item, str) else item
                    for item in attr_value
                ]
                if isinstance(op_value, str):
                    op_value = attr.precis.enforce(op_value)
            except UnicodeEncodeError:
                return None
        if attr.case_exact:
            return [(item, op_value) for item in attr_value]

        if isinstance(op_value, str):
            op_value = op_value.lower()
        return [(item.lower() if isinstance(item, str) else item, op_value) for item in attr_value]

    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """
        Tests a given `value` against the operator and returns `True`
        if it matches, `False` otherwise. If the `value` belongs to multi-valued
        attribute, the whole `value` matches if one of its items matches.

        Args:
            value: The value to test.
            schema_or_complex: Schema or `Complex` attribute that describes the value.

        Returns:
            Flag indicating whether the value matches the operator.
        """
        attr = schema_or_complex.attrs.get(self.attr_rep)
        if attr is None:
            return False

        attr_value = None if not value else value.get(self.attr_rep)

        if attr_value in [None, Missing, Invalid]:
            return False

        values = self._get_values(attr_value, attr)

        if values is None:
            return False

        for attr_value, op_value in values:
            try:
                if self.operator(attr_value, op_value):
                    return True
            except (AttributeError, TypeError):
                pass

        return False


@final
class Equal(BinaryAttributeOperator):
    """
    Represents `eq` SCIM operator.
    """

    op = "eq"
    supported_scim_types = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    supported_types = {str, bool, int, float, type(None)}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.eq(attr_value, op_value)


@final
class NotEqual(BinaryAttributeOperator):
    """
    Represents `ne` SCIM operator.
    """

    op = "ne"
    supported_scim_types = {
        "string",
        "decimal",
        "dateTime",
        "reference",
        "boolean",
        "binary",
        "integer",
        "complex",
    }
    supported_types = {str, bool, int, float, type(None)}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.ne(attr_value, op_value)


@final
class Contains(BinaryAttributeOperator):
    """
    Represents `co` SCIM operator.
    """

    op = "co"
    supported_scim_types = {"string", "reference", "complex"}
    supported_types = {str, float}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.contains(attr_value, op_value)


@final
class StartsWith(BinaryAttributeOperator):
    """
    Represents `sw` SCIM operator.
    """

    op = "sw"
    supported_scim_types = {"string", "reference", "complex"}
    supported_types = {str, float}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return attr_value.startswith(op_value)


@final
class EndsWith(BinaryAttributeOperator):
    """
    Represents `ew` SCIM operator.
    """

    op = "ew"
    supported_scim_types = {"string", "reference", "complex"}
    supported_types = {str, float}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return attr_value.endswith(op_value)


@final
class GreaterThan(BinaryAttributeOperator):
    """
    Represents `gt` SCIM operator.
    """

    op = "gt"
    supported_scim_types = {"string", "dateTime", "integer", "decimal", "complex"}
    supported_types = {str, float, int}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.gt(attr_value, op_value)


@final
class GreaterThanOrEqual(BinaryAttributeOperator):
    """
    Represents `ge` SCIM operator.
    """

    op = "ge"
    supported_scim_types = {"string", "dateTime", "integer", "decimal", "complex"}
    supported_types = {str, float, int}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.ge(attr_value, op_value)


@final
class LesserThan(BinaryAttributeOperator):
    """
    Represents `lt` SCIM operator.
    """

    op = "lt"
    supported_scim_types = {"string", "dateTime", "integer", "decimal", "complex"}
    supported_types = {str, float, int}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.lt(attr_value, op_value)


@final
class LesserThanOrEqual(BinaryAttributeOperator):
    """
    Represents `le` SCIM operator.
    """

    op = "le"
    supported_scim_types = {"string", "dateTime", "integer", "decimal", "complex"}
    supported_types = {str, float, int}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        """
        Implements operator's logic for matching the provided value.
        """
        return operator.le(attr_value, op_value)


TLogicalOrAttributeOperator = TypeVar(
    "TLogicalOrAttributeOperator", bound=Union[LogicalOperator, "AttributeOperator"]
)


@final
class ComplexAttributeOperator(Operator, Generic[TLogicalOrAttributeOperator]):
    """
    Represents complex attribute grouping operator. Can be used for single-valued and
    multi-valued complex attributes.

    Args:
        attr_rep: A representation of a complex attribute which value should be matched.
        sub_operator: A sub-operator used to test complex attribute's sub-attribute values.
    """

    def __init__(
        self,
        attr_rep: AttrRep,
        sub_operator: TLogicalOrAttributeOperator,
    ):
        self._attr_rep = attr_rep
        self._sub_operator = sub_operator

    @property
    def attr_rep(self) -> AttrRep:
        """
        The representation of the complex attribute which value should be matched.
        """
        return self._attr_rep

    @property
    def sub_operator(self) -> TLogicalOrAttributeOperator:
        """
        The sub-operator used to test complex attribute's sub-attribute values.
        """
        return self._sub_operator

    def match(
        self,
        value: Optional[ScimData],
        schema_or_complex: TSchemaOrComplex,
    ) -> bool:
        """
        Tests a given `value` against the operator and returns `True`
        if it matches, `False` otherwise. If the `value` belongs to multi-valued
        attribute, the whole `value` matches if one of its items matches.

        Args:
            value: The value to test.
            schema_or_complex: Schema or `Complex` attribute that describes the value.

        Returns:
            Flag indicating whether the value matches the operator.
        """
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
    def _normalize(attr: Complex, value: Any) -> list[ScimData]:
        value = value or ([] if attr.multi_valued else ScimData())
        return [
            ScimData(item)
            for item in (value if isinstance(value, list) else [value])
            if isinstance(item, Mapping)
        ]
