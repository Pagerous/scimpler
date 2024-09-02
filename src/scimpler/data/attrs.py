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
    MutableMapping,
    Optional,
    TypeVar,
    Union,
    final,
)
from urllib.parse import urlparse

import precis_i18n.profile
from precis_i18n import get_profile

from scimpler.constants import SCIMType
from scimpler.container import (
    AttrName,
    AttrRep,
    AttrRepFactory,
    BoundedAttrRep,
    Invalid,
    Missing,
    SchemaURI,
    SCIMData,
)
from scimpler.error import ValidationError, ValidationIssues, ValidationWarning
from scimpler.registry import resources

if TYPE_CHECKING:
    from scimpler.data.patch_path import PatchPath


TAttrFilterInput = TypeVar(
    "TAttrFilterInput", bound=Union[tuple[Union[AttrName, AttrRep], "Attribute"], "Attribute"]
)


class AttrFilter:
    def __init__(
        self,
        attr_names: Optional[Iterable[str]] = None,
        include: Optional[bool] = None,
        filter_: Optional[Callable[["Attribute"], bool]] = None,
    ):
        if attr_names and include is None:
            raise ValueError("'include' must be specified if 'attr_names' is provided")

        # stores attr names specified directly, e.g. 'emails'
        # will be here if specified as 'emails' and not 'emails.type'
        self._direct_top_level: set[AttrName] = set()

        self._complex_sub_attrs: dict[AttrName, set[AttrName]] = defaultdict(set)
        if attr_names is not None:
            for attr_name in attr_names:
                parts = attr_name.split(".", 1)
                attr_name = AttrName(parts[0])
                if len(parts) == 1:
                    self._direct_top_level.add(attr_name)
                else:
                    self._complex_sub_attrs[attr_name].add(AttrName(parts[1]))
        self._include = include
        self._filter = filter_

    def __call__(self, attrs: Iterable[TAttrFilterInput]) -> list[TAttrFilterInput]:
        filtered = []
        for item in attrs:
            identity = None

            if isinstance(item, tuple):
                identity = item[0]
                attr = item[1]
            else:
                attr = item

            if self._include is False and attr.name in self._direct_top_level:
                continue

            if isinstance(attr, Complex):
                attr = attr.clone(
                    AttrFilter(
                        attr_names=self._complex_sub_attrs[attr.name],
                        include=self._include,
                        filter_=self._filter,
                    )
                )
                # means no sub-attributes, so no need for complex attr at all
                if len(list(attr.attrs)) == 0:
                    continue
            else:
                if self._filter and not self._filter(attr):
                    continue

                if self._include is True and attr.name not in self._direct_top_level:
                    continue

            if identity is None:
                filtered.append(attr)
            else:
                filtered.append((identity, attr))
        return filtered


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
    """
    Base class for all attributes.

    Args:
        name: Name of the attribute. Must be valid attribute name, according to RFC-7643.
        description: Description of the attribute
        issuer: The attribute's issuer. It can be specified if attribute is issued by a
            service provider or provisioning client. For example, resource's `id` attribute must be
            always issued by the provider, and must not be sent in POST request
        required: Specifies if attribute is required, as per RFC-7643
        multi_valued: Specifies if attribute is multivalued, as per RFC-7643
        canonical_values: Specifies canonical values for the attribute, as per RFC-7643
        restrict_canonical_values: flag that indicates whether validation error should be
            returned if provided value is not one of canonical values. If set to `False`,
            the validation warning is returned instead. Has no effect if there are no canonical
            values
        mutability: Specifies attribute's mutability, as per RFC-7643
        returned: Specifies attribute's `returned` characteristic, as per RFC-7643
        validators: Additional validators, which are run, if the initial, built-in validation
            succeeds
        deserializer: Routine that defines attribute's value deserialization
        serializer: Routine that defines attribute's value serialization
    """

    _global_serializer: Optional[Callable[[Any], Any]] = None
    _global_deserializer: Optional[Callable[[Any], Any]] = None

    def __init__(
        self,
        name: str,
        *,
        description: str = "",
        issuer: Union[str, AttributeIssuer] = AttributeIssuer.NOT_SPECIFIED,
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
        self._issuer = AttributeIssuer(issuer)
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
    @abc.abstractmethod
    def scim_type(cls) -> str:
        """Returns type of the attribute, as defined in RFC-7643."""

    @classmethod
    @abc.abstractmethod
    def base_types(cls) -> tuple[type, ...]:
        """Returns Python types, supported by the specific `Attribute` subclass."""

    @classmethod
    def set_serializer(cls, serializer: Callable[[Any], Any]):
        """
        Sets global serializer for all attributes of the specific type.
        Can be overridden by a routine passed as `serializer` parameter in initializer.

        Has no effect if an instance of `Attribute` has serializer or deserializer defined.
        """
        cls._global_serializer = staticmethod(serializer)

    @classmethod
    def set_deserializer(cls, deserializer: Callable[[Any], Any]):
        """
        Sets global deserializer for all attributes of the specific type.
        Can be overridden by a routine passed as `deserializer` parameter in initializer.

        Has no effect if an instance of `Attribute` has serializer or deserializer defined.
        """
        cls._global_deserializer = staticmethod(deserializer)

    @property
    def name(self) -> AttrName:
        """Name of the attribute."""
        return self._name

    @property
    def description(self) -> str:
        """Description of the attribute."""
        return self._description

    @property
    def issuer(self) -> AttributeIssuer:
        """Attribute's issuer."""
        return self._issuer

    @property
    def required(self) -> bool:
        """Specifies if attribute is required, as per RFC-7643."""
        return self._required

    @property
    def multi_valued(self) -> bool:
        """Specifies if attribute is multivalued, as per RFC-7643."""
        return self._multi_valued

    @property
    def canonical_values(self) -> list:
        """Specifies canonical values for the attribute, as per RFC-7643."""
        return self._canonical_values

    @property
    def mutability(self) -> AttributeMutability:
        """Specifies attribute's mutability, as per RFC-7643."""
        return self._mutability

    @property
    def returned(self) -> AttributeReturn:
        """Specifies attribute's `returned` characteristic, as per RFC-7643."""
        return self._returned

    @property
    def has_custom_processing(self) -> bool:
        """
        Indicates whether the attribute has custom deserializer or serializer specified
        (global deserializer and serializer that are set on class level are not considered).
        """
        return bool(self._deserializer or self._serializer)

    @property
    def custom_validators(self) -> list[_AttributeValidator]:
        """
        List of custom validators of the attribute, ran if built-in validation succeeds.
        """
        return self._validators

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._name})"

    def __eq__(self, other) -> bool:
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
                self.custom_validators == other.custom_validators,
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

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if self.multi_valued:
            if not isinstance(value, list):
                issues.add_error(
                    issue=ValidationError.bad_type("list"),
                    proceed=False,
                )
                return issues
            for i, item in enumerate(value):
                issues_ = self._validate_value_type(item)
                issues.merge(
                    issues=issues_,
                    location=[i],
                )
                if not issues_.can_proceed():
                    value[i] = Invalid
            return issues
        issues.merge(self._validate_value_type(value))
        return issues

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, self.base_types()):
            issues.add_error(
                issue=ValidationError.bad_type(self.scim_type()),
                proceed=False,
            )
        return issues

    def validate(self, value: Any) -> ValidationIssues:
        """
        Validates the provided value according to attribute's specification.
        It validates the type and canonicality (if specified). If no validation issues,
        custom validators (passed as `validators` constructor parameter) are run.

        Returns:
            Validation issues
        """
        issues = ValidationIssues()
        if value in [None, Missing]:
            return issues

        issues.merge(self._validate_type(value))
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
        """
        Serializes the provided value according to attribute's specification and returns it.
        """
        if self._serializer is not None:
            return self._serializer(value)

        if self.multi_valued and isinstance(value, list):
            return [self._serialize(item) for item in value]
        return self._serialize(value)

    def _serialize(self, value: Any) -> Any:
        if self._global_serializer is None or self.has_custom_processing:
            return value
        return self._global_serializer(value)

    def deserialize(self, value: Any) -> Any:
        """
        Deserializes the provided value according to attribute's specification and returns it.
        """
        if self._deserializer is not None:
            return self._deserializer(value)

        if self.multi_valued and isinstance(value, list):
            return [self._deserialize(item) for item in value]
        return self._deserialize(value)

    def _deserialize(self, value: Any) -> Any:
        if self._global_deserializer is None or self.has_custom_processing:
            return value
        return self._global_deserializer(value)

    def to_dict(self) -> dict:
        """
        Converts the attribute to a dictionary. The contents meet the requirements
        of the schema definition, as per RFC-7643, section 7.

        Returns:
            Representation of the attribute
        """
        output = {
            "name": self._name,
            "type": str(self.scim_type()),
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
    """
    Includes uniqueness specification to the attribute, as per RFC-7643.

    Args:
        name: The name of the attribute
        uniqueness: The uniqueness of the attribute
        kwargs: The same keyword arguments base classes receive
    """

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        **kwargs: Any,
    ):
        super().__init__(name=name, **kwargs)
        self._uniqueness = uniqueness

    @property
    def uniqueness(self) -> AttributeUniqueness:
        """
        Specifies the uniqueness of the attribute, as per RFC-7643.
        """
        return self._uniqueness

    def __eq__(self, other):
        return super().__eq__(other) and self.uniqueness == other.uniqueness

    def to_dict(self) -> dict:
        """
        Extend the output from `Attribute.to_dict` and add `uniqueness` property.`

        Returns:
            Extended representation of the attribute
        """
        output = super().to_dict()
        output["uniqueness"] = self.uniqueness.value
        return output


class AttributeWithCaseExact(Attribute, abc.ABC):
    """
    Includes case sensitivity specification to the attribute, as per RFC-7643.

    Args:
        name: The name of the attribute.
        case_exact: The sensitivity of the attribute.
        kwargs: The same keyword arguments base classes receive.
    """

    def __init__(self, name: Union[str, AttrName], *, case_exact: bool = False, **kwargs: Any):
        super().__init__(name=name, **kwargs)
        self._case_exact = case_exact
        if not self._case_exact and self._canonical_values:
            self._canonical_values = [item.lower() for item in self._canonical_values]

    @property
    def case_exact(self) -> bool:
        """
        Specifies the sensitivity of the attribute, as per RFC-7643.
        """
        return self._case_exact

    def _is_canonical(self, value: Any) -> bool:
        return super()._is_canonical(value) or (
            not self._case_exact and value.lower() in self._canonical_values
        )

    def __eq__(self, other):
        return super().__eq__(other) and self.case_exact == other.case_exact

    def to_dict(self) -> dict:
        """
        Extend the output from `Attribute.to_dict` and add `case_exact` property.`

        Returns:
            Extended representation of the attribute
        """
        output = super().to_dict()
        output["caseExact"] = self.case_exact
        return output


@final
class Unknown(Attribute):
    """
    Attribute of unknown type that is used for attributes with varying content.
    For example, `urn:ietf:params:scim:api:messages:2.0:PatchOp:Operations.value` is such attribute.

    `Unknown` attribute can not be used when filtering or sorting data, so it should not be
    used when representing resource schema.
    """

    @classmethod
    def scim_type(cls) -> str:
        raise NotImplementedError("scim type for Unknown attribute is not determined")

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        raise NotImplementedError("base types for Unknown attribute are not determined")

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        return ValidationIssues()

    def _serialize(self, value: Any) -> Any:
        return value

    def _deserialize(self, value: Any) -> Any:
        return value


@final
class Boolean(Attribute):
    """
    Represents **boolean** attribute, as specified in RFC-7643.
    """

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.BOOLEAN

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (bool,)


@final
class Decimal(AttributeWithUniqueness):
    """
    Represents **decimal** attribute, as specified in RFC-7643.
    """

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.DECIMAL

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return float, int


@final
class Integer(AttributeWithUniqueness):
    """
    Represents **integer** attribute, as specified in RFC-7643.
    """

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.INTEGER

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (int,)


@final
class String(AttributeWithCaseExact, AttributeWithUniqueness):
    """
    Represents **string** attribute, as specified in RFC-7643.

    Args:
        name: The name of the attribute
        precis: PRECIS profile that should be applied for the string attribute, when
            comparing values. By default, **OpaqueString** profile is used
        kwargs: The same keyword arguments base classes receive
    """

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        precis: precis_i18n.profile.Profile = get_profile("OpaqueString"),
        **kwargs: Any,
    ):
        super().__init__(name=name, **kwargs)
        self._precis = precis

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.STRING

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (str,)

    @property
    def precis(self) -> precis_i18n.profile.Profile:
        """
        Returns PRECIS profile of the attribute.
        """
        return self._precis


@final
class Binary(AttributeWithCaseExact):
    """
    Represents **binary** attribute, as specified in RFC-7643. Binary attributes are
    case-sensitive, since they are represented by base64-encoded strings.
    """

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        url_safe: bool = False,
        omit_padding: bool = True,
        **kwargs,
    ):
        kwargs["case_exact"] = True
        super().__init__(name=name, **kwargs)
        self._url_safe = url_safe
        if self._url_safe:
            self._decoder = base64.urlsafe_b64decode
        else:
            self._decoder = base64.b64decode
        self._omit_padding = omit_padding

    def __eq__(self, other):
        if not isinstance(other, Binary):
            return False
        return (
            super().__eq__(other)
            and self._url_safe == other._url_safe
            and self._omit_padding == other._omit_padding
        )

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.BINARY

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (str,)

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_value_type(value)
        if not issues.can_proceed():
            return issues
        issues.merge(self._validate_encoding(value))
        return issues

    def _validate_encoding(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if (padding := len(value) % 4) != 0:
            if self._omit_padding:
                value += "=" * (4 - padding)
            else:
                issues.add_error(
                    issue=ValidationError.bad_encoding("base64"),
                    proceed=False,
                )
                return issues
        try:
            self._decoder(value)
        except binascii.Error:
            issues.add_error(
                issue=ValidationError.bad_encoding("base64"),
                proceed=False,
            )
        return issues


class Reference(AttributeWithCaseExact, abc.ABC):
    """
    Base class for all reference attributes.

    Args:
        name: The name of the attribute.
        reference_types: types of the references, supported by the attribute.
        kwargs: The same keyword arguments base classes receive.
    """

    def __init__(
        self, name: Union[str, AttrName], *, reference_types: Iterable[str], **kwargs: Any
    ):
        kwargs["case_exact"] = True
        super().__init__(name=name, **kwargs)
        self._reference_types = list(reference_types)

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.REFERENCE

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (str,)

    @property
    def reference_types(self) -> list[str]:
        """
        Reference types, supported by the attribute.
        """
        return self._reference_types

    def to_dict(self) -> dict:
        """
        Extend the output from `AttributeWithCaseExact.to_dict` and add reference types to it.`

        Returns:
            Extended representation of the attribute
        """
        output = super().to_dict()
        output["referenceTypes"] = self.reference_types
        return output

    def __eq__(self, other):
        return super().__eq__(other) and set(self.reference_types) == set(other.reference_types)


@final
class DateTime(Attribute):
    """
    Represents **dateTime** attribute, as specified in RFC-7643.
    """

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.DATETIME

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (str,)

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_value_type(value)
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


@final
class ExternalReference(Reference):
    """
    Represents external **reference**, as specified in RFC-7643.
    Can be used to represent references to the external resources (e.g. photos).
    """

    def __init__(self, name: Union[str, AttrName], **kwargs):
        kwargs["reference_types"] = ["external"]
        super().__init__(name=name, **kwargs)

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_value_type(value)
        if issues.can_proceed():
            result = urlparse(value)
            is_valid = all([result.scheme, result.netloc])
            if not is_valid:
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                )
        return issues


@final
class URIReference(Reference):
    """
    Represents URI **reference**, as specified in RFC-7643.
    """

    def __init__(self, name: Union[str, AttrName], **kwargs):
        kwargs["reference_types"] = ["uri"]
        super().__init__(name=name, **kwargs)


@final
class SCIMReference(Reference):
    """
    Represents SCIM **reference**, as specified in RFC-7643.
    """

    def __init__(self, name: Union[str, AttrName], *, reference_types: Iterable[str], **kwargs):
        super().__init__(name=name, reference_types=reference_types, **kwargs)

    def _validate_value_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_value_type(value)
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
    Boolean(
        "primary",
        serializer=lambda value: value or False,
        deserializer=lambda value: value or False,
    ),
    URIReference("$ref"),
]


@final
class Complex(Attribute):
    """
    Represents **complex** attribute, as specified in RFC-7643.

    Args:
        name: Name of the attribute.
        sub_attributes: Complex sub-attributes. All attributes but `Complex`
            can be sub-attributes. If not specified, and the attribute is multivalued,
            the default sub-attributes are used, as specified in
            [RFC-7643, section 2.4](https://www.rfc-editor.org/rfc/rfc7643#section-2.4).
        kwargs: The same keyword arguments the base class receives
    """

    def __init__(
        self,
        name: Union[str, AttrName],
        *,
        sub_attributes: Optional[Collection[Attribute]] = None,
        **kwargs: Any,
    ):
        for attr in sub_attributes or []:
            if isinstance(attr, Complex):
                raise TypeError("complex attributes can not contain complex sub-attributes")

        validators = kwargs.pop("validators", None)
        super().__init__(name=name, **kwargs)

        default_sub_attrs = (
            [
                String("value"),
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
            if self.attrs.get("primary") and _validate_single_primary_value not in validators:
                validators.append(_validate_single_primary_value)
            if (
                all([self.attrs.get("type"), self.attrs.get("value")])
                and _validate_type_value_pairs not in validators
            ):
                validators.append(_validate_type_value_pairs)
        self._validators = validators

    @classmethod
    def scim_type(cls) -> SCIMType:
        return SCIMType.COMPLEX

    @classmethod
    def base_types(cls) -> tuple[type, ...]:
        return (MutableMapping,)

    @property
    def attrs(self) -> "Attrs":
        """
        Complex sub-attributes.
        """
        return self._sub_attributes

    def filter(
        self,
        data: Union[MutableMapping, Iterable[MutableMapping]],
        attr_filter: AttrFilter,
    ) -> Union[SCIMData, list[SCIMData]]:
        """
        Filters the data according to the provided attribute filter. All non-matching keys in
        the item are dropped from the result. Both single-valued and multivalued complex attribute
        can be filtered.

        Args:
            data: Input data to be filtered
            attr_filter: Attribute filter, used to determine which sub-attributes should be
                dropped from a result

        Returns:
            Filtered data
        """
        if isinstance(data, MutableMapping):
            return self._filter(SCIMData(data), attr_filter)
        return [self._filter(SCIMData(item), attr_filter) for item in data]

    def _filter(
        self,
        data: SCIMData,
        attr_filter: AttrFilter,
    ) -> SCIMData:
        filtered = SCIMData()
        for name, attr in attr_filter(self.attrs):
            if (value := data.get(name)) is not Missing:
                filtered.set(name, value)
        return filtered

    def clone(self, attr_filter: AttrFilter) -> "Complex":
        """
        Clones the complex attribute. All sub-attributes that do not match a provided
        attribute filter are not included in the clone.

        Args:
            attr_filter: Attribute filter, used to determine which sub-attributes
                should be included in the clone

        Returns:
            Cloned complex attribute
        """
        cloned = copy(self)
        cloned._sub_attributes = self._sub_attributes.clone(attr_filter)
        return cloned

    def _validate(self, value: MutableMapping[str, Any]) -> ValidationIssues:
        issues = ValidationIssues()
        value = SCIMData(value)
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

    def _deserialize(self, value: MutableMapping[str, Any]) -> SCIMData:
        value = SCIMData(value)
        deserialized = SCIMData()
        for name, sub_attr in self._sub_attributes:
            sub_attr_value = value.get(name)
            if sub_attr_value is Missing:
                continue
            deserialized.set(name, sub_attr.deserialize(sub_attr_value))
        return deserialized

    def _serialize(self, value: MutableMapping[str, Any]) -> SCIMData:
        value = SCIMData(value)
        serialized = SCIMData()
        for name, sub_attr in self._sub_attributes:
            sub_attr_value = value.get(name)
            if sub_attr_value is Missing:
                continue
            serialized.set(name, sub_attr.serialize(sub_attr_value))
        return serialized

    def to_dict(self) -> dict[str, Any]:
        """
        Extend the output from `Attribute.to_dict` and add sub-attributes to it.`

        Returns:
            Extended representation of the attribute
        """
        output = super().to_dict()
        output["subAttributes"] = [sub_attr.to_dict() for _, sub_attr in self.attrs]
        return output


def _validate_single_primary_value(value: Collection[SCIMData]) -> ValidationIssues:
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


def _validate_type_value_pairs(value: Collection[SCIMData]) -> ValidationIssues:
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
    """
    Represents iterable collection of unbounded attributes.

    Examples:
        >>> attrs = Attrs([String("myString"), Integer("myInteger")])
        >>> for attr in attrs:
        >>>     print(attr)
    """

    def __init__(self, attrs: Optional[Iterable[Attribute]] = None):
        self._attrs = {attr.name: attr for attr in (attrs or [])}

    def __iter__(self) -> Iterator[tuple[AttrName, Attribute]]:
        return iter(self._attrs.items())

    def get(self, attr_name: Union[str, AttrRep]) -> Optional[Attribute]:
        """
        Returns an attribute by its name. Since attribute names are case-insensitive, it also
        applies here.

        Args:
            attr_name: Name of the attribute to be returned. Provided value must be valid
                attribute name, as specified in RFC-7643. Providing `AttrName` or `AttrRep`
                instance ensures syntactically correct attribute name

        Returns:
            Attribute, if found, None otherwise.

        Raises:
            ValueError: If the provided attribute name is not valid.
        """
        if isinstance(attr_name, AttrRep):
            attr_name = attr_name.attr
        return self._attrs.get(AttrName(attr_name))

    def clone(self, attr_filter: AttrFilter) -> "Attrs":
        """
        Clones `Attrs` according to a provided attribute filter. All attributes, including
        sub-attributes of complex attributes, are subject of filtration.

        Args:
            attr_filter: Attribute filter, used to determine which attributes and sub-attributes
                should be included in the clone

        Returns:
            Cloned `Attrs` with inner attributes, optionally filtered by `attr_filter`.
        """
        return Attrs(attr_filter(self._attrs.values()))


class BoundedAttrs:
    """
    Represents iterable collection of attributes bounded to a specific schema.

    Args:
        schema: A SCIM schema attributes belong to
        attrs: Attributes bound to the schema
        common_attrs: Names of attributes that belong to the schema, but not exclusively.
            For example, `id`, `meta`, and `externalId` are such attributes, defined in every
            resource schema. Used to determine core attributes:
            core attrs = all attrs - common attrs

    It is possible to iterate through the attributes stored in the instance.

    Examples:
        >>> bounded_attrs = BoundedAttrs(
        >>>     schema=SchemaURI("my:resource:schema"),
        >>>     attrs=[
        >>>         String("myString"),
        >>>         Complex("myComplex", sub_attributes=[Integer("myInteger")])
        >>>     ],
        >>>)
        >>>
        >>> for attr_rep, attr in bounded_attrs:
        >>>     print(attr_rep, attr)
    """

    def __init__(
        self,
        schema: SchemaURI,
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
        """
        Returns bounded attribute representation, given only an attribute name.
        Searches through attributes defined in the schema, then in the extensions.
        First matching result is returned, so if a schema extension defines an attribute
        with the same name as base schema, it is not accessible.

        Args:
            name: Name of the attribute. A sub-attribute can be specified as well, using `__`
                to separate the attribute name and the sub-attribute name, for example:
                name__formatted

        Examples:
            >>> bounded_attrs = BoundedAttrs(
            >>>     schema=SchemaURI("my:resource:schema"),
            >>>     attrs=[
            >>>         String("myString"),
            >>>         Complex("myComplex", sub_attributes=[Integer("myInteger")])
            >>>     ],
            >>>)
            >>>
            >>> bounded_attrs.myString
            BoundedAttrRep(my:resource_schema:myString)
            >>> bounded_attrs.myComplex__myInteger
            BoundedAttrRep(my:resource_schema:myComplex.myInteger)


        Raises:
            AttributeError: If bounded attribute is not found
            ValueError: If provided attribute name is not valid

        Returns:
            Bounded attribute representation for the given (sub-)attribute name
        """
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
        """
        Iterator that goes through the core attributes of the schema.
        """
        return iter(self._core_attrs.items())

    @property
    def extensions(self) -> dict[SchemaURI, "BoundedAttrs"]:
        """
        Associated extensions.
        """
        return self._extensions

    def extend(self, schema: SchemaURI, attrs: "BoundedAttrs") -> None:
        """
        Extends bounded attributes with provided attributes, associated with a provided schema.
        Args:
            schema: Extension schema URI.
            attrs: Extension attributes.
        """
        self._extensions[schema] = attrs
        for attr_rep, attr in attrs:
            self._attrs[attr_rep] = attr
        self._bounded_complex_sub_attrs.update(attrs._bounded_complex_sub_attrs)

    def clone(
        self, attr_filter: AttrFilter, ignore_filter: Optional[Iterable[str]] = None
    ) -> "BoundedAttrs":
        """
        Clones `BoundedAttrs` according to a provided attribute filter. All attributes, including
        sub-attributes of complex attributes, are subject of filtration. Extensions are filtered
        as well.

        Args:
            attr_filter: Attribute filter, used to determine which attributes and sub-attributes
                should be included in the clone
            ignore_filter: Names of common or core attributes that should be included in the clone,
                regardless the filter

        Returns:
            Cloned `BoundedAttrs` with inner attributes, optionally filtered by `attr_filter`.
        """
        filtered_attrs = attr_filter(
            attrs=(
                attr
                for attr_rep, attr in self._attrs.items()
                if attr_rep.schema not in self._extensions
            )
        )
        to_include = []
        for attr_name in ignore_filter or []:
            for attr in filtered_attrs:
                if attr.name == attr_name:
                    break
            else:
                if (
                    attr_name in self._common_attrs
                    or BoundedAttrRep(schema=self._schema, attr=attr_name) in self._core_attrs
                ) and (attr_to_include := self.get(attr_name)) is not None:
                    to_include.append(attr_to_include)

        filtered_attrs = to_include + filtered_attrs
        cloned = BoundedAttrs(
            schema=self._schema,
            attrs=filtered_attrs,
            common_attrs=self._common_attrs,
        )
        for schema, attrs in self._extensions.items():
            cloned.extend(
                schema=schema,
                attrs=attrs.clone(attr_filter),
            )
        return cloned

    def get(self, attr_rep: Union[str, AttrRep]) -> Optional[Attribute]:
        """
        Returns an attribute, given its name or (bounded) representation.
        If string is provided, it must be valid attribute name. If `AttrRep` is provided (unbounded
        attribute representation), then the core schema and extensions are checked,
        and first matching result is returned.

        Args:
            attr_rep: Representation of the attribute to be returned

        Raises:
            ValueError: If provided attribute name is not valid

        Returns: Attribute, if found, None otherwise.
        """
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
        """
        Returns an attribute, given a patch path. The syntax of the path must correspond with the
        actual attribute. For example, patch path deserialized from `name[formatted eq 'John Doe']`
        would yield no results, because _name_ is not multivalued attribute (assuming User schema).

        Args:
            path: path deserialized from the value, which is usually sent in resource PATCH requests

        Returns: Attribute, if found, None otherwise.
        """
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
