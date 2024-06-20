import abc
import base64
import binascii
from collections import defaultdict
from copy import copy
from datetime import datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Iterable,
    Iterator,
    Optional,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urlparse

import precis_i18n.profile
from precis_i18n import get_profile
from typing_extensions import TypeAlias

from src.constants import SCIMType
from src.container import (
    AttrName,
    AttrRep,
    AttrRepFactory,
    BoundedAttrRep,
    Invalid,
    Missing,
    SchemaURI,
    SCIMDataContainer,
)
from src.error import ValidationError, ValidationIssues, ValidationWarning
from src.registry import resources

if TYPE_CHECKING:
    from src.data.patch_path import PatchPath


class AttributeMutability(str, Enum):
    READ_WRITE = "readWrite"
    READ_ONLY = "readOnly"
    WRITE_ONLY = "writeOnly"
    IMMUTABLE = "immutable"


class AttributeReturn(str, Enum):
    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    REQUEST = "request"


class AttributeUniqueness(str, Enum):
    NONE = "none"
    SERVER = "server"
    GLOBAL = "global"


class AttributeIssuer(Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    NOT_SPECIFIED = "NOT_SPECIFIED"


_AttributeProcessor = Callable[[Any], Any]
_AttributeValidator = Callable[[Any], ValidationIssues]


class Attribute(abc.ABC):
    SCIM_TYPE: str
    BASE_TYPES: tuple
    _global_serializer: Callable[[Any], Any] = None
    _global_deserializer: Callable[[Any], Any] = None

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        description: str = "",
        issuer: AttributeIssuer = AttributeIssuer.NOT_SPECIFIED,
        required: bool = False,
        multi_valued: bool = False,
        canonical_values: Optional[Collection] = None,
        restrict_canonical_values: bool = False,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        validators: Optional[list[_AttributeValidator]] = None,
        deserializer: Optional[_AttributeProcessor] = None,
        serializer: Optional[_AttributeProcessor] = None,
    ):
        self._name = AttrName(name)
        self._description = description
        self._issuer = issuer
        self._required = required
        self._canonical_values = list(canonical_values or [])
        self._validate_canonical_values = restrict_canonical_values
        self._multi_valued = multi_valued
        self._mutability = mutability
        self._returned = returned
        self._validators = validators or []
        self._deserializer = deserializer
        self._serializer = serializer

    @classmethod
    def set_serializer(cls, serializer: Callable[[Any], Any]):
        cls._global_serializer = staticmethod(serializer)

    @classmethod
    def set_deserializer(cls, deserializer: Callable[[Any], Any]):
        cls._global_deserializer = staticmethod(deserializer)

    @property
    def name(self) -> AttrName:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def issuer(self) -> AttributeIssuer:
        return self._issuer

    @property
    def required(self) -> bool:
        return self._required

    @property
    def multi_valued(self) -> bool:
        return self._multi_valued

    @property
    def canonical_values(self) -> list:
        return self._canonical_values

    @property
    def mutability(self) -> AttributeMutability:
        return self._mutability

    @property
    def returned(self) -> AttributeReturn:
        return self._returned

    @property
    def has_custom_processing(self) -> bool:
        return bool(self._deserializer or self._serializer)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._name})"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            [
                self._name == other._name,
                self._required == other._required,
                self._canonical_values == other._canonical_values,
                self._multi_valued == other._multi_valued,
                self._mutability == other._mutability,
                self._returned == other._returned,
                self._validators == other._validators,
                self._deserializer == other._deserializer,
                self._serializer == other._serializer,
                self._validate_canonical_values == other._validate_canonical_values,
                self.has_custom_processing == other.has_custom_processing,
            ]
        )

    def _is_canonical(self, value: Any) -> bool:
        if not self._canonical_values:
            return True
        return value in self._canonical_values

    def validate_type(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if self.multi_valued:
            if not isinstance(value, list):
                issues.add_error(
                    issue=ValidationError.bad_type("list"),
                    proceed=False,
                )
                return issues
            for i, item in enumerate(value):
                issues_ = self._validate_type(item)
                issues.merge(
                    issues=issues_,
                    location=[i],
                )
                if not issues_.can_proceed():
                    value[i] = Invalid
            return issues
        issues.merge(self._validate_type(value))
        return issues

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, self.BASE_TYPES):
            issues.add_error(
                issue=ValidationError.bad_type(self.SCIM_TYPE),
                proceed=False,
            )
        return issues

    def validate(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if value in [None, Missing]:
            return issues

        issues.merge(self.validate_type(value))
        if not issues.can_proceed():
            return issues

        if self._multi_valued:
            for i, item in enumerate(value):
                if item is Invalid:
                    continue
                issues_ = self._validate(item)
                issues.merge(issues=issues_, location=[i])
                if not issues_.can_proceed():
                    value[i] = Invalid
        else:
            issues.merge(self._validate(value))
        for validator in self._validators:
            if not issues.can_proceed():
                break
            issues.merge(validator(value))
        return issues

    def _validate(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not self._is_canonical(value):
            if self._validate_canonical_values:
                issues.add_error(
                    issue=ValidationError.must_be_one_of(self._canonical_values),
                    proceed=False,
                )
            else:
                issues.add_warning(
                    issue=ValidationWarning.should_be_one_of(self._canonical_values),
                )
        return issues

    def serialize(self, value: Any) -> Any:
        if self._serializer is not None:
            return self._serializer(value)

        if self.multi_valued and isinstance(value, list):
            return [self._serialize(item) for item in value]
        return self._serialize(value)

    def _serialize(self, value: Any) -> Any:
        if self._global_serializer is None:
            return value
        return self._global_serializer(value)

    def deserialize(self, value: Any) -> Any:
        if self._deserializer is not None:
            return self._deserializer(value)

        if self.multi_valued and isinstance(value, list):
            return [self._deserialize(item) for item in value]
        return self._deserialize(value)

    def _deserialize(self, value: Any) -> Any:
        if self._global_deserializer is None:
            return value
        return self._global_deserializer(value)

    def to_dict(self) -> dict:
        output = {
            "name": self._name,
            "type": str(self.SCIM_TYPE),
            "multiValued": self._multi_valued,
            "description": self.description,
            "required": self.required,
            "mutability": self.mutability.value,
            "returned": self.returned.value,
        }
        if self.canonical_values:
            output["canonicalValues"] = self.canonical_values
        return output


class AttributeWithUniqueness(Attribute, abc.ABC):
    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self._uniqueness = uniqueness

    @property
    def uniqueness(self) -> AttributeUniqueness:
        return self._uniqueness

    def __eq__(self, other):
        return super().__eq__(other) and self.uniqueness == other.uniqueness

    def to_dict(self):
        output = super().to_dict()
        output["uniqueness"] = self.uniqueness.value
        return output


class AttributeWithCaseExact(Attribute, abc.ABC):
    def __init__(self, name: Union[str, AttrName], *, case_exact: bool = False, **kwargs):
        super().__init__(name=name, **kwargs)
        self._case_exact = case_exact
        if not self._case_exact and self._canonical_values:
            self._canonical_values = [item.lower() for item in self._canonical_values]

    @property
    def case_exact(self) -> bool:
        return self._case_exact

    def _is_canonical(self, value: Any) -> bool:
        return super()._is_canonical(value) or (
            not self._case_exact and value.lower() in self._canonical_values
        )

    def __eq__(self, other):
        return super().__eq__(other) and self.case_exact == other.case_exact

    def to_dict(self):
        output = super().to_dict()
        output["caseExact"] = self.case_exact
        return output


class Unknown(Attribute):
    def _validate_type(self, value: Any) -> ValidationIssues:
        return ValidationIssues()

    def _serialize(self, value: Any) -> Any:
        return value

    def _deserialize(self, value: Any) -> Any:
        return value


class Boolean(Attribute):
    SCIM_TYPE = SCIMType.BOOLEAN
    BASE_TYPES = (bool,)


class Decimal(AttributeWithUniqueness):
    SCIM_TYPE = SCIMType.DECIMAL
    BASE_TYPES = (float, int)


class Integer(AttributeWithUniqueness):
    SCIM_TYPE = SCIMType.INTEGER
    BASE_TYPES = (int,)


class String(AttributeWithCaseExact, AttributeWithUniqueness):
    SCIM_TYPE = "string"
    BASE_TYPES = (str,)

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        precis: precis_i18n.profile.Profile = get_profile("OpaqueString"),
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self._precis = precis

    @property
    def precis(self) -> precis_i18n.profile.Profile:
        return self._precis


class Binary(AttributeWithCaseExact):
    SCIM_TYPE = SCIMType.BINARY
    BASE_TYPES = (str,)

    def __init__(self, name: Union[str, AttrName], **kwargs):
        kwargs["case_exact"] = True
        super().__init__(name=name, **kwargs)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if not issues.can_proceed():
            return issues
        issues.merge(self._validate_encoding(value))
        return issues

    @staticmethod
    def _validate_encoding(value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if len(value) % 4 != 0:
            issues.add_error(
                issue=ValidationError.bad_encoding("base64"),
                proceed=False,
            )
            return issues
        try:
            base64.b64decode(value, validate=True)
        except binascii.Error:
            issues.add_error(
                issue=ValidationError.bad_encoding("base64"),
                proceed=False,
            )
        return issues


class _Reference(AttributeWithCaseExact, abc.ABC):
    SCIM_TYPE = SCIMType.REFERENCE
    BASE_TYPES = (str,)

    def __init__(self, name: Union[str, AttrName], *, reference_types: Iterable[str], **kwargs):
        kwargs["case_exact"] = True
        super().__init__(name=name, **kwargs)
        self._reference_types = list(reference_types)

    @property
    def reference_types(self) -> list[str]:
        return self._reference_types

    def to_dict(self) -> dict:
        output = super().to_dict()
        output["referenceTypes"] = self.reference_types
        return output

    def __eq__(self, other):
        return super().__eq__(other) and set(self.reference_types) == set(other.reference_types)


class DateTime(Attribute):
    SCIM_TYPE = SCIMType.DATETIME
    BASE_TYPES = (str,)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if not issues.can_proceed():
            return issues
        value = self._deserialize_xsd_datetime(value)
        if value is None:
            issues.add_error(
                issue=ValidationError.bad_value_syntax(),
                proceed=False,
            )
            return issues
        return issues

    @staticmethod
    def _deserialize_xsd_datetime(value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class ExternalReference(_Reference):
    def __init__(self, name: Union[str, AttrName], **kwargs):
        kwargs["reference_types"] = ["external"]
        super().__init__(name=name, **kwargs)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if issues.can_proceed():
            result = urlparse(value)
            is_valid = all([result.scheme, result.netloc])
            if not is_valid:
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                )
        return issues


class URIReference(_Reference):
    def __init__(self, name: Union[str, AttrName], **kwargs):
        kwargs["reference_types"] = ["uri"]
        super().__init__(name=name, **kwargs)


class SCIMReference(_Reference):
    def __init__(self, name: Union[str, AttrName], *, reference_types: Iterable[str], **kwargs):
        super().__init__(name=name, reference_types=reference_types, **kwargs)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if not issues.can_proceed():
            return issues

        for resource_schema in resources.values():
            if resource_schema.name in self._reference_types and resource_schema.endpoint in value:
                return issues

        issues.add_error(
            issue=ValidationError.bad_scim_reference(self._reference_types),
            proceed=False,
        )
        return issues


_default_sub_attrs = [
    Unknown("value"),
    String(
        "display",
        mutability=AttributeMutability.IMMUTABLE,
    ),
    String("type"),
    Boolean("primary"),
    URIReference("$ref"),
]


_AllowedData: TypeAlias = Union[SCIMDataContainer, dict]
TData = TypeVar("TData", bound=Union[_AllowedData, list[_AllowedData]])


class Complex(Attribute):
    SCIM_TYPE = "complex"
    BASE_TYPES = (SCIMDataContainer, dict)

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        sub_attributes: Optional[Collection[Attribute]] = None,
        **kwargs,
    ):
        validators = kwargs.pop("validators", None)
        super().__init__(name=name, **kwargs)

        default_sub_attrs = (
            [
                Unknown("value"),
                String(
                    "display",
                    mutability=AttributeMutability.IMMUTABLE,
                ),
                String("type"),
                Boolean("primary"),
                URIReference("$ref"),
            ]
            if self._multi_valued
            else []
        )
        self._sub_attributes = Attrs(sub_attributes or default_sub_attrs)

        validators = list(validators or [])
        if self._multi_valued:
            if self.attrs.get("primary") and validate_single_primary_value not in validators:
                validators.append(validate_single_primary_value)
            if (
                all([self.attrs.get("type"), self.attrs.get("value")])
                and validate_type_value_pairs not in validators
            ):
                validators.append(validate_type_value_pairs)
        self._validators = validators

    @property
    def attrs(self) -> "Attrs":
        return self._sub_attributes

    def filter(self, data: TData, attr_filter: Callable[[Attribute], bool]) -> TData:
        if isinstance(data, list):
            return cast(TData, [self.filter(item, attr_filter) for item in data])

        if isinstance(data, dict):
            return cast(TData, self._filter(SCIMDataContainer(data), attr_filter).to_dict())
        return cast(TData, self._filter(cast(SCIMDataContainer, data), attr_filter))

    def _filter(
        self,
        data: SCIMDataContainer,
        attr_filter: Callable[[Attribute], bool],
    ) -> SCIMDataContainer:
        filtered = SCIMDataContainer()
        for name, attr in self.attrs:
            if attr_filter(attr) and (value := data.get(name)) is not Missing:
                filtered.set(name, value)
        return filtered

    def clone(self, attr_filter: Callable[["Attribute"], bool]) -> "Complex":
        cloned = copy(self)
        cloned._sub_attributes = self._sub_attributes.clone(attr_filter)
        return cloned

    def _validate(self, value: Union[SCIMDataContainer, dict[str, Any]]) -> ValidationIssues:
        issues = ValidationIssues()
        value = SCIMDataContainer(value)
        for name, sub_attr in self._sub_attributes:
            sub_attr_value = value.get(name)
            if sub_attr_value is Missing:
                continue
            issues_ = sub_attr.validate(sub_attr_value)
            if not issues_.can_proceed():
                value.set(name, Invalid)
            issues.merge(
                location=[name],
                issues=issues_,
            )
        return issues

    def _deserialize(self, value: Union[dict, SCIMDataContainer]) -> SCIMDataContainer:
        value = SCIMDataContainer(value)
        deserialized = SCIMDataContainer()
        for name, sub_attr in self._sub_attributes:
            sub_attr_value = value.get(name)
            if sub_attr_value is Missing:
                continue
            deserialized.set(name, sub_attr.deserialize(sub_attr_value))
        return deserialized

    def _serialize(self, value: Union[dict, SCIMDataContainer]) -> dict[str, Any]:
        value = SCIMDataContainer(value)
        serialized = SCIMDataContainer()
        for name, sub_attr in self._sub_attributes:
            sub_attr_value = value.get(name)
            if sub_attr_value is Missing:
                continue
            serialized.set(name, sub_attr.serialize(sub_attr_value))
        return serialized.to_dict()

    def to_dict(self) -> dict[str, Any]:
        output = super().to_dict()
        output["subAttributes"] = [sub_attr.to_dict() for _, sub_attr in self.attrs]
        return output


def validate_single_primary_value(value: Collection[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    primary_entries = 0
    for item in value:
        if item is not Invalid and item.get("primary") is True:
            primary_entries += 1
    if primary_entries > 1:
        issues.add_error(
            issue=ValidationError.multiple_primary_values(),
            proceed=True,
        )
    return issues


def validate_type_value_pairs(value: Collection[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    pairs: dict[tuple[Any, Any], int] = defaultdict(int)
    for item in value:
        if item is Invalid:
            continue
        type_ = item.get("type")
        value = item.get("value")
        if type_ and value:
            pairs[item.get("type"), item.get("value")] += 1
    for count in pairs.values():
        if count > 1:
            issues.add_warning(issue=ValidationWarning.multiple_type_value_pairs())
    return issues


class Attrs:
    def __init__(self, attrs: Optional[Iterable[Attribute]] = None):
        self._attrs = {attr.name: attr for attr in (attrs or [])}

    def __iter__(self) -> Iterator[tuple[AttrName, Attribute]]:
        return iter(self._attrs.items())

    def get(self, attr_name: Union[str, AttrRep]) -> Optional[Attribute]:
        if isinstance(attr_name, AttrRep):
            attr_name = attr_name.attr
        return self._attrs.get(AttrName(attr_name))

    def clone(self, attr_filter: Callable[[Attribute], bool]) -> "Attrs":
        cloned = Attrs()
        cloned._attrs = {key: attr for key, attr in self._attrs.items() if attr_filter(attr)}
        return cloned


class BoundedAttrs:
    def __init__(
        self,
        schema: str,
        attrs: Optional[Iterable[Attribute]] = None,
        common_attrs: Optional[Iterable[str]] = None,
    ):
        self._schema = schema
        self._core_attrs: dict[BoundedAttrRep, Attribute] = {}
        self._common_attrs = {AttrName(item) for item in (common_attrs or set())}
        self._extensions: dict[SchemaURI, BoundedAttrs] = {}

        self._attrs: dict[BoundedAttrRep, Attribute] = {}
        self._bounded_complex_sub_attrs: dict[BoundedAttrRep, dict[BoundedAttrRep, Attribute]] = (
            defaultdict(dict)
        )

        for attr in attrs or []:
            attr_rep = BoundedAttrRep(
                schema=self._schema,
                attr=attr.name,
            )
            self._attrs[attr_rep] = attr
            if attr.name not in self._common_attrs:
                self._core_attrs[attr_rep] = attr

            if isinstance(attr, Complex):
                self._bounded_complex_sub_attrs[attr_rep] = {
                    BoundedAttrRep(
                        schema=attr_rep.schema,
                        attr=attr_rep.attr,
                        sub_attr=sub_attr_name,
                    ): sub_attr
                    for sub_attr_name, sub_attr in attr.attrs
                }

    def __getattr__(self, name: str) -> BoundedAttrRep:
        parts = name.split("__", 1)
        n_parts = len(parts)
        attr_name = parts[0].lower()
        attr_rep = BoundedAttrRep(schema=self._schema, attr=attr_name)
        if attr := self._attrs.get(attr_rep):
            attr_rep = BoundedAttrRep(
                schema=self._schema,
                attr=attr.name,
            )
            if n_parts == 1:
                return attr_rep

            sub_attr_rep = BoundedAttrRep(
                schema=attr_rep.schema,
                attr=attr_rep.attr,
                sub_attr=parts[1],
            )
            if sub_attr := self._bounded_complex_sub_attrs[attr_rep].get(sub_attr_rep):
                return BoundedAttrRep(
                    schema=attr_rep.schema,
                    attr=attr_rep.attr,
                    sub_attr=sub_attr.name,
                )

        for attrs in self._extensions.values():
            if attr_rep_extension := getattr(attrs, name, None):
                return attr_rep_extension

        raise AttributeError(
            f"attribute {name.replace('__', '.')!r} "
            f"does not exist within {self._schema!r} and its extensions"
        )

    def __iter__(self) -> Iterator[tuple[BoundedAttrRep, Attribute]]:
        return iter(self._attrs.items())

    @property
    def core_attrs(self) -> Iterator[tuple[BoundedAttrRep, Attribute]]:
        return iter(self._core_attrs.items())

    @property
    def extensions(self) -> dict[SchemaURI, "BoundedAttrs"]:
        return self._extensions

    def extend(self, schema: SchemaURI, attrs: "BoundedAttrs") -> None:
        self._extensions[schema] = attrs
        for attr_rep, attr in attrs:
            self._attrs[attr_rep] = attr
        self._bounded_complex_sub_attrs.update(attrs._bounded_complex_sub_attrs)

    def clone(self, attr_filter: Callable[[Attribute], bool]) -> "BoundedAttrs":
        cloned = BoundedAttrs(
            schema=self._schema,
            attrs=(
                attr.clone(attr_filter=attr_filter) if isinstance(attr, Complex) else attr
                for attr_rep, attr in self._attrs.items()
                if attr_rep.schema not in self._extensions and attr_filter(attr)
            ),
            common_attrs=self._common_attrs,
        )
        for schema, attrs in self._extensions.items():
            cloned.extend(
                schema=schema,
                attrs=attrs.clone(attr_filter),
            )
        return cloned

    def get(self, attr_rep: Union[str, AttrRep]) -> Optional[Attribute]:
        if isinstance(attr_rep, str):
            attr_rep = AttrRepFactory.deserialize(attr_rep)

        if isinstance(attr_rep, BoundedAttrRep):
            top_level_rep = BoundedAttrRep(
                schema=attr_rep.schema,
                attr=attr_rep.attr,
            )
            attr = self._attrs.get(top_level_rep)
            if attr is None or not attr_rep.is_sub_attr:
                return attr
            return self._bounded_complex_sub_attrs[top_level_rep].get(attr_rep)

        top_level_rep = BoundedAttrRep(
            schema=self._schema,
            attr=attr_rep.attr,
        )
        if attr := self._attrs.get(top_level_rep):
            if not attr_rep.is_sub_attr:
                return attr

            return self._bounded_complex_sub_attrs[top_level_rep].get(
                BoundedAttrRep(
                    schema=self._schema,
                    attr=attr_rep.attr,
                    sub_attr=attr_rep.sub_attr,
                )
            )

        for attrs in self._extensions.values():
            if attr := attrs.get(attr_rep):
                return attr

        return None

    def get_by_path(self, path: "PatchPath") -> Optional[Attribute]:
        attr = self.get(path.attr_rep)
        if attr is None or (path.has_filter and not attr.multi_valued):
            return None

        if path.sub_attr_name is None:
            return attr

        if isinstance(path.attr_rep, BoundedAttrRep):
            return self.get(
                BoundedAttrRep(
                    schema=path.attr_rep.schema,
                    attr=path.attr_rep.attr,
                    sub_attr=path.sub_attr_name,
                )
            )
        return self.get(
            AttrRep(
                attr=path.attr_rep.attr,
                sub_attr=path.sub_attr_name,
            )
        )
