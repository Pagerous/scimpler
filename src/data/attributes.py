from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.type import AttributeType, Complex, get_scim_type
from src.error import ValidationError, ValidationIssues

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
    NONE = ("none",)
    SERVER = "server"
    GLOBAL = "global"


class AttributeIssuer(Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    NOT_SPECIFIED = "NOT_SPECIFIED"


_AttributeProcessor = Callable[[Any], Tuple[Any, ValidationIssues]]


class Attribute:
    def __init__(
        self,
        name: Union[str, AttrRep],
        type_: Type[AttributeType],
        reference_types: Optional[Iterable[str]] = None,
        issuer: AttributeIssuer = AttributeIssuer.NOT_SPECIFIED,
        required: bool = False,
        case_exact: bool = False,
        multi_valued: bool = False,
        canonical_values: Optional[Collection] = None,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        parsers: Optional[Collection[_AttributeProcessor]] = None,
        dumpers: Optional[Collection[_AttributeProcessor]] = None,
    ):
        self._rep = AttrRep(attr=name) if isinstance(name, str) else name
        self._type = type_
        self._reference_types = list(reference_types or [])  # TODO validate applicability
        self._issuer = issuer
        self._required = required
        self._case_exact = case_exact
        self._canonical_values = list(canonical_values) if canonical_values else canonical_values
        self._multi_valued = multi_valued
        self._mutability = mutability
        self._returned = returned
        self._uniqueness = uniqueness
        self._parsers = parsers or []
        self._dumpers = dumpers or []

    @property
    def rep(self) -> AttrRep:
        return self._rep

    @property
    def type(self) -> Type[AttributeType]:
        return self._type

    @property
    def reference_types(self) -> List[str]:
        return self._reference_types

    @property
    def issuer(self) -> AttributeIssuer:
        return self._issuer

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

    @property
    def parsers(self) -> List[_AttributeProcessor]:
        return self._parsers

    @property
    def dumpers(self) -> List[_AttributeProcessor]:
        return self._dumpers

    def __repr__(self) -> str:
        return f"Attribute(name={self._rep}, type={self._type.__name__})"

    def __eq__(self, other):
        if not isinstance(other, Attribute):
            return False

        return all(
            [
                self._rep == other._rep,
                self._type is other._type,
                self._reference_types == other._reference_types,
                self._required == other._required,
                self._case_exact == other._case_exact,
                self._canonical_values == other._canonical_values,
                self._multi_valued == other._multi_valued,
                self._mutability == other._mutability,
                self._returned == other._returned,
                self._uniqueness == other._uniqueness,
                self._parsers == other._parsers,
                self._dumpers == other._dumpers,
            ]
        )

    def _process(self, value: Any, method, postprocessors) -> Tuple[Any, ValidationIssues]:
        issues = ValidationIssues()
        if value is None:
            return value, issues

        if self._multi_valued:
            if not isinstance(value, list):
                issues.add(
                    issue=ValidationError.bad_type(get_scim_type(list), get_scim_type(type(value))),
                    proceed=False,
                )
                return Invalid, issues
            parsed = []
            for i, item in enumerate(value):
                item, issues_ = method(item)
                issues.merge(location=(i,), issues=issues_)
                if self._canonical_values is not None and item not in self._canonical_values:
                    pass  # TODO: warn about non-canonical value
                parsed.append(item)
        else:
            parsed, issues_ = method(value)
            issues.merge(issues=issues_)
            if self._canonical_values is not None and parsed not in self._canonical_values:
                pass  # TODO: warn about non-canonical value

        if not issues.has_issues():
            for postprocessor in postprocessors:
                try:
                    parsed, issues_ = postprocessor(parsed)
                    issues.merge(issues=issues_)
                except:  # noqa: break on first failure
                    parsed = Invalid
                    break
        return parsed, issues

    def parse(self, value: Any) -> Tuple[Any, ValidationIssues]:
        return self._process(
            value=value,
            method=self._type.parse,
            postprocessors=self._parsers,
        )

    def dump(self, value: Any) -> Tuple[Any, ValidationIssues]:
        return self._process(
            value=value,
            method=self._type.dump,
            postprocessors=self._dumpers,
        )


_ComplexAttributeProcessor = Callable[[Any], Tuple[Any, ValidationIssues]]


class ComplexAttribute(Attribute):
    def __init__(
        self,
        sub_attributes: Collection[Attribute],
        name: Union[str, AttrRep],
        required: bool = False,
        issuer: AttributeIssuer = AttributeIssuer.NOT_SPECIFIED,
        multi_valued: bool = False,
        mutability: AttributeMutability = AttributeMutability.READ_WRITE,
        returned: AttributeReturn = AttributeReturn.DEFAULT,
        uniqueness: AttributeUniqueness = AttributeUniqueness.NONE,
        parsers: Optional[Collection[_AttributeProcessor]] = None,
        dumpers: Optional[Collection[_AttributeProcessor]] = None,
        complex_parsers: Optional[Collection[_ComplexAttributeProcessor]] = None,
        complex_dumpers: Optional[Collection[_ComplexAttributeProcessor]] = None,
    ):
        super().__init__(
            name=name,
            type_=Complex,
            issuer=issuer,
            required=required,
            multi_valued=multi_valued,
            mutability=mutability,
            returned=returned,
            uniqueness=uniqueness,
            parsers=parsers,
            dumpers=dumpers,
        )
        self._sub_attributes = Attributes(sub_attributes)

        complex_parsers, complex_dumpers = complex_parsers or [], complex_dumpers or []
        if multi_valued:
            if validate_single_primary_value not in complex_parsers:
                complex_parsers.append(validate_single_primary_value)
            if validate_single_primary_value not in complex_dumpers:
                complex_dumpers.append(validate_single_primary_value)
        self._complex_parsers = complex_parsers
        self._complex_dumpers = complex_dumpers

    @property
    def attrs(self) -> "Attributes":
        return self._sub_attributes

    @property
    def complex_parsers(self) -> List[_ComplexAttributeProcessor]:
        return self._complex_parsers

    @property
    def complex_dumpers(self) -> List[_ComplexAttributeProcessor]:
        return self._complex_dumpers

    def _process_complex(
        self, value: Any, method: str, postprocessors
    ) -> Tuple[Any, ValidationIssues]:
        value, issues = getattr(super(), method)(value)
        if not issues.can_proceed() or value is None:
            return value, issues
        if self.multi_valued:
            parsed = []
            for i, item in enumerate(value):
                item = SCIMDataContainer(item)
                parsed_item = SCIMDataContainer()
                for sub_attr in self._sub_attributes:
                    sub_attr_value = item[sub_attr.rep]
                    if sub_attr_value is Missing:
                        continue
                    parsed_attr, issues_ = getattr(sub_attr, method)(sub_attr_value)
                    issues.merge(location=(i, sub_attr.rep.attr), issues=issues_)
                    parsed_item[sub_attr.rep] = parsed_attr
                parsed.append(parsed_item)
        else:
            value = SCIMDataContainer(value)
            parsed = SCIMDataContainer()
            for sub_attr in self._sub_attributes:
                sub_attr_value = value[sub_attr.rep]
                if sub_attr_value is Missing:
                    continue
                parsed_attr, issues_ = getattr(sub_attr, method)(sub_attr_value)
                issues.merge(
                    location=(sub_attr.rep.attr,),
                    issues=issues_,
                )
                parsed[sub_attr.rep] = parsed_attr

        if not issues:
            for postprocessor in postprocessors:
                try:
                    parsed, issues_ = postprocessor(parsed)
                    issues.merge(issues=issues_)
                except Exception as e:  # noqa: break on first failure
                    parsed = Invalid
                    break

        return parsed, issues

    def parse(
        self, value: Any
    ) -> Tuple[Union[Invalid, SCIMDataContainer, List[SCIMDataContainer]], ValidationIssues]:
        return self._process_complex(value, "parse", self._complex_parsers)

    def dump(
        self, value: Any
    ) -> Tuple[Union[Invalid, SCIMDataContainer, List[SCIMDataContainer]], ValidationIssues]:
        return self._process_complex(value, "dump", self._complex_dumpers)


def validate_single_primary_value(
    value: Collection[SCIMDataContainer],
) -> Tuple[List[SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    primary_entries = set()
    for i, item in enumerate(value):
        if item["primary"] is True:
            primary_entries.add(i)
    if len(primary_entries) > 1:
        issues.add(
            issue=ValidationError.multiple_primary_values(primary_entries),
            proceed=True,
        )
    # TODO: warn if a given type-value pair appears more than once
    return list(value), issues


class Attributes:
    def __init__(self, attrs: Iterable[Attribute]):
        self._top_level: List[Attribute] = []
        self._attrs = {}
        for attr in attrs:
            self._attrs[attr.rep.schema, attr.rep.attr, attr.rep.sub_attr] = attr
            if not attr.rep.sub_attr:
                self._top_level.append(attr)

    @property
    def top_level(self) -> List[Attribute]:
        return self._top_level

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
