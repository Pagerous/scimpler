import re
from enum import Enum
from typing import Any, Callable, Collection, Dict, Iterable, List, Optional, Type

from src.parser.attributes import type as at
from src.parser.error import ValidationError, ValidationIssues

_ATTR_NAME = re.compile(r"(\w+|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_FULL_ATTR_NAME_REGEX = re.compile(rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.\w+)?)")


class AttributeName:
    def __init__(self, schema: str = "", attr: str = "", sub_attr: str = ""):
        if not _ATTR_NAME.fullmatch(attr):
            raise ValueError(f"{attr!r} is not valid attr name")

        schema, attr, sub_attr = schema.lower(), attr.lower(), sub_attr.lower()
        attr_ = attr
        if schema:
            attr_ = f"{schema}:{attr_}"
        if sub_attr:
            attr_ += "." + sub_attr

        if not _FULL_ATTR_NAME_REGEX.fullmatch(attr):
            raise ValueError(f"{attr_!r} is not valid attr / sub-attr name")

        self._schema = schema
        self._attr = attr
        self._sub_attr = sub_attr
        self._repr = attr_

    def __repr__(self) -> str:
        return self._repr

    def __eq__(self, other):
        if not isinstance(other, AttributeName):
            return False

        if all([self.schema, other.schema]) and self.schema != other.schema:
            return False

        if self.attr != other.attr:
            return False

        if self.sub_attr != other.sub_attr:
            return False

        return True

    @classmethod
    def parse(cls, attr: str) -> Optional["AttributeName"]:
        match = _FULL_ATTR_NAME_REGEX.fullmatch(attr)
        if not match:
            return None

        schema, attr_name = match.group(1), match.group(2)
        schema = schema[:-1].lower() if schema else ""
        if "." in attr_name:
            attr, sub_attr = attr_name.split(".")
        else:
            attr, sub_attr = attr_name, ""
        return AttributeName(schema=schema, attr=attr, sub_attr=sub_attr)

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def full_attr(self) -> str:
        if self._schema:
            return f"{self._schema}:{self.attr}"
        return self.attr

    @property
    def attr(self) -> str:
        return self._attr

    @property
    def sub_attr(self) -> str:
        return self._sub_attr

    def top_level_equals(self, other: "AttributeName") -> bool:
        if all([self.schema, other.schema]):
            return self.full_attr == other.full_attr
        return self.attr == other.attr

    def extract(self, data: Dict[str, Any]) -> Optional[Any]:
        top_value = None
        used_extension = False
        for k, v in data.items():
            k_lower = k.lower()
            if k_lower == self.schema:
                used_extension = True
                top_value = v
                break
            if k_lower in {self.full_attr, self.attr}:
                top_value = v
                break
            k_parsed = AttributeName.parse(k)
            if k_parsed and self.top_level_equals(k_parsed):
                top_value = v
                break
            if (
                _URI_PREFIX.fullmatch(f"{k}:")
                and isinstance(v, Dict)
                and self.attr in map(str.lower, v)
            ):
                used_extension = True
                top_value = v
                break

        if used_extension and isinstance(top_value, Dict):
            for k, v in top_value.items():
                if k.lower() == self.attr:
                    top_value = v
                    break

        if not self.sub_attr:
            return top_value

        if isinstance(top_value, Dict):
            for k, v in top_value.items():
                if k.lower() == self.sub_attr:
                    return v

        return None


class AttributeMutability(str, Enum):
    READ_WRITE = "readWrite"
    READ_ONLY = "readOnly"
    WRITE_ONLY = "writeOnly"
    IMMUTABLE = "immutable"


class AttributeIssuer(str, Enum):
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    PROVISIONING_CLIENT = "PROVISIONING_CLIENT"
    BOTH = "BOTH"


class AttributeReturn(str, Enum):
    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    REQUEST = "request"


class AttributeUniqueness(str, Enum):
    NONE = ("none",)
    SERVER = "server"
    GLOBAL = "global"


class Attribute:
    def __init__(
        self,
        name: str,
        type_: Type[at.AttributeType],
        reference_types: Optional[Iterable[str]] = None,
        issuer: AttributeIssuer = AttributeIssuer.BOTH,
        required: bool = False,
        case_exact: bool = False,
        multi_valued: bool = False,
        canonical_values: Optional[Collection] = None,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        validators: Optional[Collection[Callable[[Any], ValidationIssues]]] = None,
    ):
        self._name = name
        self._issuer = issuer
        self._type = type_
        self._reference_types = list(reference_types or [])  # TODO validate applicability
        self._required = required
        self._case_exact = case_exact
        self._canonical_values = list(canonical_values) if canonical_values else canonical_values
        self._multi_valued = multi_valued
        self._mutability = mutability
        self._returned = returned
        self._uniqueness = uniqueness
        self._validators = validators or []

    @property
    def name(self) -> str:
        return self._name.lower()

    @property
    def display_name(self) -> str:
        return self._name

    @property
    def issuer(self) -> AttributeIssuer:
        return self._issuer

    @property
    def type(self) -> Type[at.AttributeType]:
        return self._type

    @property
    def reference_types(self) -> List[str]:
        return self._reference_types

    @property
    def required(self) -> bool:
        return self._required

    @property
    def case_exact(self) -> bool:
        return self._case_exact

    @property
    def multi_valued(self) -> bool:
        return self._multi_valued

    @property
    def canonical_values(self) -> Optional[list]:
        return self._canonical_values

    @property
    def mutability(self) -> AttributeMutability:
        return self._mutability

    @property
    def returned(self) -> AttributeReturn:
        return self._returned

    @property
    def uniqueness(self) -> AttributeUniqueness:
        return self._uniqueness

    def __repr__(self) -> str:
        return f"Attribute(name={self._name}, type={self._type.__name__})"

    def __eq__(self, other):
        if not isinstance(other, Attribute):
            return False

        return all(
            [
                self._name.lower() == other._name.lower(),
                self._issuer == other._issuer,
                self._type is other._type,
                self._reference_types == other._reference_types,
                self._required == other._required,
                self._case_exact == other._case_exact,
                self._canonical_values == other._canonical_values,
                self._multi_valued == other._multi_valued,
                self._mutability == other._mutability,
                self._returned == other._returned,
                self._uniqueness == other._uniqueness,
                self._validators == other._validators,
            ]
        )

    def validate(self, value: Any, direction: str) -> ValidationIssues:
        issues = ValidationIssues()
        if value is None:
            if (
                not self._required
                or (direction == "REQUEST" and self.issuer == AttributeIssuer.SERVICE_PROVIDER)
                or (direction == "RESPONSE" and self._returned == AttributeReturn.NEVER)
            ):
                return issues
            issues.add(
                issue=ValidationError.missing_required_attribute(self._name),
                proceed=False,
            )
            return issues
        else:
            if direction == "RESPONSE" and self._returned == AttributeReturn.NEVER:
                issues.add(
                    issue=ValidationError.returned_restricted_attribute(self._name),
                    proceed=False,
                )
                return issues

        if self._multi_valued:
            if not isinstance(value, (list, tuple)):
                issues.add(
                    issue=ValidationError.bad_multivalued_attribute_type(type(value)),
                    proceed=False,
                )
                return issues
            for i, item in enumerate(value):
                issues.merge(
                    location=(i,),
                    issues=self._type.validate(item),
                )
                if self._canonical_values is not None and item not in self._canonical_values:
                    pass  # TODO: warn about non-canonical value
        else:
            issues.merge(issues=self._type.validate(value))
            if self._canonical_values is not None and value not in self._canonical_values:
                pass  # TODO: warn about non-canonical value
        for validator in self._validators:
            try:
                issues.merge(issues=validator(value))
            except:  # noqa: not interested in exceptions, only validation procedures that finished matter
                pass
        return issues


class ComplexAttribute(Attribute):
    def __init__(
        self,
        sub_attributes: Collection[Attribute],
        name: str,
        issuer: AttributeIssuer = AttributeIssuer.BOTH,
        required: bool = False,
        case_exact: bool = False,
        multi_valued: bool = False,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        validators: Optional[Collection[Callable[[Any], ValidationIssues]]] = None,
    ):
        super().__init__(
            name=name,
            issuer=issuer,
            type_=at.Complex,
            required=required,
            case_exact=case_exact,
            multi_valued=multi_valued,
            mutability=mutability,
            returned=returned,
            uniqueness=uniqueness,
            validators=validators,
        )
        self._sub_attributes: Dict[str, Attribute] = {attr.name: attr for attr in sub_attributes}

    @property
    def sub_attributes(self) -> Dict[str, Attribute]:
        return self._sub_attributes

    def validate(self, value: Any, direction: str) -> ValidationIssues:
        issues = super().validate(value, direction)
        if not issues.can_proceed() or value is None:
            return issues
        if self.multi_valued:
            for i, item in enumerate(value):
                for attr_name, attr in self._sub_attributes.items():
                    issues.merge(
                        location=(i, attr.name),
                        issues=attr.validate(
                            AttributeName(attr=attr_name).extract(item), direction
                        ),  # TODO: use AttributeName in constructor
                    )
        else:
            for attr_name, attr in self._sub_attributes.items():
                issues.merge(
                    location=(attr.name,),
                    issues=attr.validate(AttributeName(attr=attr_name).extract(value), direction),
                )
        return issues
