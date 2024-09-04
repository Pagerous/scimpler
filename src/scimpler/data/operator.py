import abc
import operator
from typing import Any, Generator, Generic, Optional, TypeVar, Union

from scimpler.container import AttrRep, Invalid, Missing, SCIMData
from scimpler.data.attrs import Attribute, AttributeWithCaseExact, Complex, String
from scimpler.data.schemas import ResourceSchema

TSchemaOrComplex = TypeVar("TSchemaOrComplex", bound=Union[ResourceSchema, Complex])


class Operator(abc.ABC, Generic[TSchemaOrComplex]):
    """
    Base class for operators.
    """

    @abc.abstractmethod
    def match(
        self,
        value: Optional[SCIMData],
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
    def __init__(self, *sub_operators: Operator):
        self._sub_operators = list(sub_operators)

    @classmethod
    @abc.abstractmethod
    def op(cls) -> str:
        """Representation of the operator's type."""

    @property
    def sub_operators(self) -> list[Operator]:
        """Sub-operators contained inside this operator."""
        return self._sub_operators

    def _collect_matches(
        self,
        value: Optional[SCIMData],
        schema_or_complex: TSchemaOrComplex,
    ) -> Generator[bool, None, None]:
        for sub_operator in self.sub_operators:
            yield sub_operator.match(value, schema_or_complex)


class And(LogicalOperator):
    """
    Represents `and` SCIM operator. Matches if all sub-operators match.
    """
    def match(
        self,
        value: Optional[SCIMData],
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
    """
    Represents `or` SCIM operator. Matches if any of sub-operators match.
    """
    def match(
        self,
        value: Optional[SCIMData],
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
        value = value or SCIMData()
        for match in self._collect_matches(value, schema_or_complex):
            if match:
                return True
        return False

    @classmethod
    def op(cls) -> str:
        return "or"


class Not(LogicalOperator):
    """
    Represents `not` SCIM operator. Matches if a sub-operator does not match.
    """
    def __init__(self, sub_operator: Operator):
        super().__init__(sub_operator)

    @classmethod
    def op(cls) -> str:
        return "not"

    def match(
        self,
        value: Optional[SCIMData],
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
        return not next(self._collect_matches(value, schema_or_complex))


class AttributeOperator(Operator, abc.ABC):
    """
    Base class for all operators that involve attributes directly.
    """
    def __init__(self, attr_rep: AttrRep):
        self._attr_rep = attr_rep

    @classmethod
    @abc.abstractmethod
    def op(cls) -> str:
        """Returns representation of the operator's type."""

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep

    @classmethod
    @abc.abstractmethod
    def supported_scim_types(cls) -> set[str]:
        """
        Returns a list of SCIM types supported by the operator.
        """

    @classmethod
    @abc.abstractmethod
    def supported_types(cls) -> set[type]:
        """
        Returns a list of Python types (e.g. str, int) supported by the operator
        """


class UnaryAttributeOperator(AttributeOperator, abc.ABC):
    """
    Base class for all unary operators.
    """

    @staticmethod
    @abc.abstractmethod
    def operator(value: Any) -> bool:
        """
        Operator's logic for matching values.
        """

    def match(
        self,
        value: Optional[SCIMData],
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
        if attr is None:
            return False

        if attr.scim_type() not in self.supported_scim_types():
            return False

        if not value:
            return False

        attr_value = value.get(self.attr_rep)

        if attr.multi_valued:
            if isinstance(attr_value, list):
                match = any(
                    [
                        self.operator(item)
                        for item in attr_value
                        if type(item) in self.supported_types()
                    ]
                )
            else:
                match = False
        else:
            match = self.operator(attr_value)

        return match


class Present(UnaryAttributeOperator):
    """
    Represents `pr` SCIM operator.
    """

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {
            "string",
            "decimal",
            "dateTime",
            "reference",
            "boolean",
            "binary",
            "integer",
            "complex",
        }

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, bool, int, dict, float, type(None)}

    @staticmethod
    def operator(value: Any) -> bool:
        if isinstance(value, dict):
            return any([Present.operator(val) for val in value.values()])
        if isinstance(value, str):
            return value != ""
        return value not in [None, Missing]

    @classmethod
    def op(cls) -> str:
        return "pr"


class BinaryAttributeOperator(AttributeOperator, abc.ABC):
    """
    Base class for all binary operators.

    Args:
        attr_rep: A representation of an attribute which value should be
            compared with the operator's value.
        value: The operator's value (right operand), compared to the attribute's value
            (left operand).
    """

    def __init__(self, attr_rep: AttrRep, value: Any):
        super().__init__(attr_rep=attr_rep)
        if type(value) not in self.supported_types():
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
        Operator's logic for matching values.
        """

    def _get_values_for_comparison(
        self, value: Any, attr: Attribute
    ) -> Optional[list[tuple[Any, Any]]]:
        if attr.scim_type() not in self.supported_scim_types():
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
                if self.operator(attr_value, op_value):
                    return True
            except (AttributeError, TypeError):
                pass

        return False


class Equal(BinaryAttributeOperator):
    """
    Represents `eq` SCIM operator.
    """

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {
            "string",
            "decimal",
            "dateTime",
            "reference",
            "boolean",
            "binary",
            "integer",
            "complex",
        }

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, bool, int, float, type(None)}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.eq(attr_value, op_value)

    @classmethod
    def op(cls) -> str:
        return "eq"


class NotEqual(BinaryAttributeOperator):
    """
    Represents `ne` SCIM operator.
    """

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {
            "string",
            "decimal",
            "dateTime",
            "reference",
            "boolean",
            "binary",
            "integer",
            "complex",
        }

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, bool, int, float, type(None)}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.ne(attr_value, op_value)

    @classmethod
    def op(cls) -> str:
        return "ne"


class Contains(BinaryAttributeOperator):
    """
    Represents `co` SCIM operator.
    """

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "reference", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.contains(attr_value, op_value)

    @classmethod
    def op(cls) -> str:
        return "co"


class StartsWith(BinaryAttributeOperator):
    """
    Represents `sw` SCIM operator.
    """

    @staticmethod
    def operator(val1: str, val2: str):
        return val1.startswith(val2)

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "reference", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float}

    @classmethod
    def op(cls) -> str:
        return "sw"


class EndsWith(BinaryAttributeOperator):
    """
    Represents `ew` SCIM operator.
    """

    @staticmethod
    def operator(val1: str, val2: str):
        return val1.endswith(val2)

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "reference", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float}

    @classmethod
    def op(cls) -> str:
        return "ew"


class GreaterThan(BinaryAttributeOperator):
    """
    Represents `gt` SCIM operator.
    """

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "dateTime", "integer", "decimal", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float, int}

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.gt(attr_value, op_value)

    @classmethod
    def op(cls) -> str:
        return "gt"


class GreaterThanOrEqual(BinaryAttributeOperator):
    """
    Represents `ge` SCIM operator.
    """

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.ge(attr_value, op_value)

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "dateTime", "integer", "decimal", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "ge"


class LesserThan(BinaryAttributeOperator):
    """
    Represents `lt` SCIM operator.
    """

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.lt(attr_value, op_value)

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "dateTime", "integer", "decimal", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "lt"


class LesserThanOrEqual(BinaryAttributeOperator):
    """
    Represents `le` SCIM operator.
    """

    @staticmethod
    def operator(attr_value: Any, op_value: Any) -> bool:
        return operator.le(attr_value, op_value)

    @classmethod
    def supported_scim_types(cls) -> set[str]:
        return {"string", "dateTime", "integer", "decimal", "complex"}

    @classmethod
    def supported_types(cls) -> set[type]:
        return {str, float, int}

    @classmethod
    def op(cls) -> str:
        return "le"


TLogicalOrAttributeOperator = TypeVar(
    "TLogicalOrAttributeOperator", bound=Union[LogicalOperator, "AttributeOperator"]
)


class ComplexAttributeOperator(Operator, Generic[TLogicalOrAttributeOperator]):
    """
    Represents complex attribute grouping operator. Can be used for single-valued and
    multi-valued complex attributes.

    Args:
        attr_rep: A representation of a complex attribute which value should be matched.
        sub_operator: A sub-operator used to test complex attribute sub-attribute values.
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
        The representation of a complex attribute which value should be matched.
        """
        return self._attr_rep

    @property
    def sub_operator(self) -> TLogicalOrAttributeOperator:
        """
        The sub-operator used to test complex attribute sub-attribute values.
        """
        return self._sub_operator

    def match(
        self,
        value: Optional[SCIMData],
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
    def _normalize(attr: Complex, value: Any) -> list[SCIMData]:
        value = value or ([] if attr.multi_valued else SCIMData())
        return [
            SCIMData(item)
            for item in (value if isinstance(value, list) else [value])
            if isinstance(item, (dict, SCIMData))
        ]
