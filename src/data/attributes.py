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
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse

from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues, ValidationWarning

if TYPE_CHECKING:
    from src.data.path import PatchPath


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
    SCIM_NAME: str
    TYPE: Type

    def __init__(
        self,
        name: Union[str, AttrRep],
        *,
        description: str = "",
        issuer: AttributeIssuer = AttributeIssuer.NOT_SPECIFIED,
        required: bool = False,
        multi_valued: bool = False,
        canonical_values: Optional[Collection] = None,
        restrict_canonical_values: bool = False,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        validators: Optional[List[_AttributeValidator]] = None,
        parser: Optional[_AttributeProcessor] = None,
        dumper: Optional[_AttributeProcessor] = None,
    ):
        self._rep = AttrRep.parse(name) if isinstance(name, str) else name
        self._description = description
        self._issuer = issuer
        self._required = required
        self._canonical_values = canonical_values
        self._validate_canonical_values = restrict_canonical_values
        self._multi_valued = multi_valued
        self._mutability = mutability
        self._returned = returned
        self._uniqueness = uniqueness
        self._validators = validators or []
        self._parser = parser
        self._dumper = dumper

    @property
    def rep(self) -> AttrRep:
        return self._rep

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

    @property
    def validators(self) -> List[_AttributeValidator]:
        return self._validators

    @property
    def parser(self) -> Optional[_AttributeProcessor]:
        return self._parser

    @property
    def dumper(self) -> Optional[_AttributeProcessor]:
        return self._dumper

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._rep})"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            [
                self._rep == other._rep,
                self._required == other._required,
                self._canonical_values == other._canonical_values,
                self._multi_valued == other._multi_valued,
                self._mutability == other._mutability,
                self._returned == other._returned,
                self._uniqueness == other._uniqueness,
                self._validators == other._validators,
                self._parser == other._parser,
                self._dumper == other._dumper,
                self._validate_canonical_values == other._validate_canonical_values,
            ]
        )

    def _is_canonical(self, value: Any) -> bool:
        if self._canonical_values is None:
            return True
        return value in self._canonical_values

    @classmethod
    def _validate_type(cls, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, cls.TYPE):
            issues.add_error(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.TYPE),
                    provided=get_scim_type(type(value)),
                ),
                proceed=False,
            )
        return issues

    def validate(self, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if value is None:
            return issues

        if self._multi_valued:
            if not isinstance(value, list):
                issues.add_error(
                    issue=ValidationError.bad_type(get_scim_type(list), get_scim_type(type(value))),
                    proceed=False,
                )
                return issues

            for i, item in enumerate(value):
                issues_ = self._validate_type(item)
                issues.merge(location=(i,), issues=issues_)
                if not issues_.can_proceed():
                    continue
                if not self._is_canonical(item):
                    if self._validate_canonical_values:
                        issues.add_error(
                            issue=ValidationError.must_be_one_of(self._canonical_values),
                            proceed=False,
                            location=(i,),
                        )
                    else:
                        issues.add_warning(
                            issue=ValidationWarning.should_be_one_of(self._canonical_values),
                            location=(i,),
                        )
        else:
            issues_ = self._validate_type(value)
            issues.merge(issues=issues_)
            if not issues_.can_proceed():
                return issues

            elif not self._is_canonical(value):
                if self._validate_canonical_values:
                    issues.add_error(
                        issue=ValidationError.must_be_one_of(self._canonical_values),
                        proceed=False,
                    )
                else:
                    issues.add_warning(
                        issue=ValidationWarning.should_be_one_of(self._canonical_values),
                    )

        for validator in self.validators:
            if not issues.can_proceed():
                break
            issues.merge(validator(value))
        return issues

    def dump(self, value: Any) -> Any:
        if self._dumper is not None:
            return self._dumper(value)
        return value

    def parse(self, value: Any) -> Any:
        if self._parser is not None:
            return self._parser(value)
        return value

    def to_dict(self) -> Dict:
        output = {
            "name": self.rep.attr,
            "type": self.SCIM_NAME,
            "multiValued": self._multi_valued,
            "description": self.description,
            "required": self.required,
            "mutability": self.mutability.value,
            "returned": self.returned.value,
            "uniqueness": self.uniqueness.value,
        }
        if self.canonical_values:
            output["canonicalValues"] = self.canonical_values
        return output

    def clone(self, attr_rep: AttrRep) -> "Attribute":
        clone = copy(self)
        clone._rep = attr_rep
        return clone


class Unknown(Attribute):
    @classmethod
    def _validate_type(cls, value: Any) -> ValidationIssues:
        return ValidationIssues()


class Boolean(Attribute):
    SCIM_NAME = "boolean"
    TYPE = bool


class Decimal(Attribute):
    SCIM_NAME = "decimal"
    TYPE = float

    @classmethod
    def _validate_type(cls, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, (cls.TYPE, int)):
            issues.add_error(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.TYPE),
                    provided=get_scim_type(type(value)),
                ),
                proceed=False,
            )
        return issues


class Integer(Attribute):
    SCIM_NAME = "integer"
    TYPE = int


class String(Attribute):
    SCIM_NAME = "string"
    TYPE = str

    def __init__(self, name: Union[str, AttrRep], *, case_exact: bool = False, **kwargs):
        super().__init__(name=name, **kwargs)
        self._case_exact = case_exact
        if not case_exact and self._canonical_values:
            self._canonical_values = [item.lower() for item in self._canonical_values]

    @property
    def case_exact(self) -> bool:
        return self._case_exact

    def _is_canonical(self, value: Any) -> bool:
        return super()._is_canonical(value) or (
            not self._case_exact and value.lower() in self._canonical_values
        )

    def to_dict(self) -> Dict:
        output = super().to_dict()
        output["caseExact"] = self.case_exact
        return output

    def __eq__(self, other):
        return super().__eq__(other) and self.case_exact == other.case_exact


class Binary(String):
    SCIM_NAME = "binary"
    TYPE = str

    def __init__(self, name: Union[str, AttrRep], **kwargs):
        kwargs.pop("case_exact", None)
        super().__init__(name=name, case_exact=True, **kwargs)

    @classmethod
    def _validate_type(cls, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if not issues.can_proceed():
            return issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return issues
        return issues

    @classmethod
    def _validate_encoding(cls, value: Any, issues: ValidationIssues) -> ValidationIssues:
        try:
            value = bytes(value, "ascii")
            if base64.b64encode(base64.b64decode(value)) != value:
                issues.add_error(
                    issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                    proceed=False,
                )
        except binascii.Error:
            issues.add_error(
                issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                proceed=False,
            )
        return issues


class _Reference(String):
    SCIM_NAME = "reference"
    TYPE = str

    def __init__(self, name: Union[str, AttrRep], *, reference_types: Iterable[str], **kwargs):
        kwargs["case_exact"] = True
        super().__init__(name=name, **kwargs)
        self._reference_types = list(reference_types)

    @property
    def reference_types(self) -> List[str]:
        return self._reference_types

    def to_dict(self) -> Dict:
        output = super().to_dict()
        output["referenceTypes"] = self.reference_types
        return output

    def __eq__(self, other):
        return super().__eq__(other) and set(self.reference_types) == set(other.reference_types)


class DateTime(String):
    SCIM_NAME = "dateTime"
    TYPE = str

    def __init__(self, name: Union[str, AttrRep], **kwargs):
        kwargs["case_exact"] = False
        super().__init__(name=name, **kwargs)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if not issues.can_proceed():
            return issues
        value = self._parse_xsd_datetime(value)
        if value is None:
            issues.add_error(
                issue=ValidationError.bad_value_syntax(),
                proceed=False,
            )
            return issues
        return issues

    @staticmethod
    def _parse_xsd_datetime(value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class ExternalReference(_Reference):
    def __init__(self, name: Union[str, AttrRep], **kwargs):
        kwargs["reference_types"] = ["external"]
        super().__init__(name=name, **kwargs)

    def _validate_type(self, value: Any) -> ValidationIssues:
        issues = super()._validate_type(value)
        if issues.can_proceed():
            try:
                result = urlparse(value)
                is_valid = all([result.scheme, result.netloc])
                if not is_valid:
                    issues.add_error(
                        issue=ValidationError.bad_url(value),
                        proceed=False,
                    )
                    return issues
            except ValueError:
                issues.add_error(
                    issue=ValidationError.bad_url(value),
                    proceed=False,
                )
        return issues


class URIReference(_Reference):
    def __init__(self, name: Union[str, AttrRep], **kwargs):
        kwargs["reference_types"] = ["uri"]
        super().__init__(name=name, **kwargs)


class SCIMReference(_Reference):
    def __init__(self, name: Union[str, AttrRep], *, reference_types: Iterable[str], **kwargs):
        super().__init__(name=name, reference_types=reference_types, **kwargs)


_ComplexAttributeProcessor = Callable[[Any], Tuple[Any, ValidationIssues]]


class Complex(Attribute):
    SCIM_NAME = "complex"
    TYPE = SCIMDataContainer

    def __init__(
        self,
        name: Union[str, AttrRep],
        *,
        sub_attributes: Collection[Attribute],
        **kwargs,
    ):
        validators = kwargs.pop("validators", None)
        super().__init__(name=name, **kwargs)
        self._sub_attributes = Attributes(sub_attributes)
        validators = list(validators or [])
        if self._multi_valued:
            if validate_single_primary_value not in validators:
                validators.append(validate_single_primary_value)
        self._complex_validators = validators

    @property
    def attrs(self) -> "Attributes":
        return self._sub_attributes

    def validate(self, value: Any) -> ValidationIssues:
        issues = super().validate(value)
        if not issues.can_proceed() or value is None:
            return issues
        if self.multi_valued:
            for i, item in enumerate(value):
                item = SCIMDataContainer(item)
                for sub_attr in self._sub_attributes:
                    sub_attr_value = item.get(sub_attr.rep)
                    if sub_attr_value is Missing:
                        continue
                    issues_ = sub_attr.validate(sub_attr_value)
                    if not issues_.can_proceed():
                        item.set(sub_attr.rep, Invalid)
                    issues.merge(location=(i, sub_attr.rep.attr), issues=issues_)
        else:
            value = SCIMDataContainer(value)
            for sub_attr in self._sub_attributes:
                sub_attr_value = value.get(sub_attr.rep)
                if sub_attr_value is Missing:
                    continue
                issues_ = sub_attr.validate(sub_attr_value)
                if not issues_.can_proceed():
                    value.set(sub_attr.rep, Invalid)
                issues.merge(
                    location=(sub_attr.rep.attr,),
                    issues=issues_,
                )

        for validator in self._complex_validators:
            if not issues.can_proceed():
                break
            issues.merge(validator(value))
        return issues

    def parse(self, value: Any) -> Any:
        if self.multi_valued:
            parsed = []
            for i, item in enumerate(value):
                item = SCIMDataContainer(item)
                parsed_item = SCIMDataContainer()
                for sub_attr in self._sub_attributes:
                    sub_attr_value = item.get(sub_attr.rep)
                    if sub_attr_value is Missing:
                        continue
                    parsed_item.set(sub_attr.rep, sub_attr.parse(sub_attr_value))
                parsed.append(parsed_item)
        else:
            value = SCIMDataContainer(value)
            parsed = SCIMDataContainer()
            for sub_attr in self._sub_attributes:
                sub_attr_value = value.get(sub_attr.rep)
                if sub_attr_value is Missing:
                    continue
                parsed.set(sub_attr.rep, sub_attr.parse(sub_attr_value))
        return super().parse(parsed)

    def dump(self, value: Any) -> Any:
        if self.multi_valued:
            dumped = []
            for i, item in enumerate(value):
                item = SCIMDataContainer(item)
                parsed_item = SCIMDataContainer()
                for sub_attr in self._sub_attributes:
                    sub_attr_value = item.get(sub_attr.rep)
                    if sub_attr_value is Missing:
                        continue
                    parsed_item.set(sub_attr.rep, sub_attr.dump(sub_attr_value))
                dumped.append(parsed_item)
        else:
            value = SCIMDataContainer(value)
            dumped = SCIMDataContainer()
            for sub_attr in self._sub_attributes:
                sub_attr_value = value.get(sub_attr.rep)
                if sub_attr_value is Missing:
                    continue
                dumped.set(sub_attr.rep, sub_attr.dump(sub_attr_value))
        return super().dump(dumped)

    def to_dict(self) -> Dict[str, Any]:
        output = super().to_dict()
        output["subAttributes"] = [sub_attr.to_dict() for sub_attr in self.attrs]
        return output


def validate_single_primary_value(value: Collection[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    primary_entries = set()
    for i, item in enumerate(value):
        if item.get("primary") is True:
            primary_entries.add(i)
    if len(primary_entries) > 1:
        issues.add_error(
            issue=ValidationError.multiple_primary_values(primary_entries),
            proceed=True,
        )
    # TODO: warn if a given type-value pair appears more than once
    return issues


class Attributes:
    def __init__(self, attrs: Iterable[Attribute]):
        self._top_level: List[Attribute] = []
        self._base_top_level: List[Attribute] = []
        self._extensions: Dict[str, List[Attribute]] = defaultdict(list)
        self._attrs = {}
        for attr in attrs:
            self._attrs[attr.rep.schema, attr.rep.attr, attr.rep.sub_attr] = attr
            if not attr.rep.sub_attr:
                self._top_level.append(attr)
                if not attr.rep.extension:
                    self._base_top_level.append(attr)
            if attr.rep.extension:
                self._extensions[attr.rep.schema.lower()].append(attr)

    @property
    def top_level(self) -> List[Attribute]:
        return self._top_level

    @property
    def base_top_level(self) -> List[Attribute]:
        return self._base_top_level

    @property
    def extensions(self) -> Dict[str, List[Attribute]]:
        return self._extensions

    def __getattr__(self, name: str) -> Attribute:
        parts = name.split("__", 1)
        if len(parts) == 1:
            for attr in self._top_level:
                if attr.rep.attr.lower() == name.lower():
                    return attr
            raise AttributeError(f"no {name!r} attribute")

        has_attr = False
        for (_, attr, sub_attr), attr_obj in self._attrs.items():
            if attr.lower() == parts[0].lower():
                has_attr = True
                if sub_attr.lower() == parts[1].lower():
                    return attr_obj

        if has_attr:
            raise AttributeError(f"{parts[0]!r} has no {parts[1]!r} attribute")
        raise AttributeError(f"no {parts[0]!r} attribute")

    def __iter__(self):
        return iter(self._attrs.values())

    def get(self, attr_rep: AttrRep) -> Optional[Attribute]:
        for (schema, attr, sub_attr), attr_obj in self._attrs.items():
            if AttrRep(schema, attr, sub_attr) == attr_rep:
                return attr_obj
        return None

    def get_by_path(self, path: "PatchPath") -> Optional[Attribute]:
        if (
            path.complex_filter is not None
            and self.get(path.complex_filter.operator.attr_rep) is None
        ):
            return None
        attr = self.get(path.attr_rep)
        if attr is None or path.complex_filter_attr_rep is None:
            return attr
        return self.get(path.complex_filter_attr_rep)


_TYPE_TO_SCIM_TYPE: Dict[Type, str] = {
    bool: Boolean.SCIM_NAME,
    int: Integer.SCIM_NAME,
    float: Decimal.SCIM_NAME,
    str: String.SCIM_NAME,
    SCIMDataContainer: Complex.SCIM_NAME,
    list: "list",
}


def get_scim_type(type_: Type) -> str:
    return _TYPE_TO_SCIM_TYPE.get(type_, "unknown")
