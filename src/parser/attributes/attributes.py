from enum import Enum
from typing import Collection, Callable, Any, Optional, Type

from src.parser.error import ValidationError, ValidationIssues
from src.parser.attributes import type as at


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
    NONE = "none",
    SERVER = "server"
    GLOBAL = "global"


class Attribute:
    def __init__(
        self,
        name: str,
        type_: Type[at.AttributeType],
        issuer: AttributeIssuer = AttributeIssuer.BOTH,
        required: bool = False,
        case_exact: bool = False,
        multi_valued: bool = False,
        canonical_values: Optional[Collection] = None,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        validators: Optional[Collection[Callable[[Any], ValidationIssues]]] = None
    ):
        self._name = name
        self._issuer = issuer
        self._type = type_
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
        return self._name

    @property
    def issuer(self) -> AttributeIssuer:
        return self._issuer

    @property
    def type(self) -> Type[at.AttributeType]:
        return self._type

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

    def validate(self, value: Any, direction: str) -> ValidationIssues:
        issues = ValidationIssues()
        if value is None:
            if (
                not self._required or (
                    direction == "REQUEST" and
                    self.issuer == AttributeIssuer.SERVICE_PROVIDER
                ) or (
                    direction == "RESPONSE" and
                    self._returned == AttributeReturn.NEVER
                )
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
            validators=validators
        )
        self._sub_attributes: dict[str, Attribute] = {
            attr.name: attr for attr in sub_attributes
        }

    def validate(self, value: Any,  direction: str) -> ValidationIssues:
        issues = super().validate(value, direction)
        if not issues.can_proceed() or value is None:
            return issues
        if self.multi_valued:
            for i, item in enumerate(value):
                for attr_name, attr in self._sub_attributes.items():
                    issues.merge(
                        location=(i, attr.name),
                        issues=attr.validate(item.get(attr_name), direction),
                    )
        else:
            for attr_name, attr in self._sub_attributes.items():
                issues.merge(
                    location=(attr.name, ),
                    issues=attr.validate(value.get(attr_name), direction),
                )
        return issues
