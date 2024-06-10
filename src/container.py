import re
from dataclasses import dataclass
from typing import Any, Optional, Union

from src.error import ValidationError, ValidationIssues
from src.registry import schemas

_ATTR_NAME = re.compile(r"([a-zA-Z][\w$-]*|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_ATTR_REP = re.compile(
    rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.([a-zA-Z][\w$-]*|\$ref))?)"
)


class AttrName(str):
    def __new__(cls, value: str) -> "AttrName":
        if not isinstance(value, AttrName) and not _ATTR_NAME.fullmatch(value):
            raise ValueError(f"{value!r} is not valid attr name")
        return str.__new__(cls, value)  # type: ignore

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = other.lower()
        return self.lower() == other

    def __hash__(self):
        return hash(self.lower())


class SchemaURI(str):
    def __new__(cls, value: str) -> "SchemaURI":
        if not isinstance(value, SchemaURI) and not _URI_PREFIX.fullmatch(value + ":"):
            raise ValueError(f"{value!r} is not a valid schema URI")
        return str.__new__(cls, value)  # type: ignore

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = other.lower()
        return self.lower() == other

    def __hash__(self):
        return hash(self.lower())


class AttrRep:
    def __init__(self, attr: str, sub_attr: Optional[str] = None):
        attr = AttrName(attr)
        repr_: str = attr
        if sub_attr is not None:
            sub_attr = AttrName(sub_attr)
            repr_ += "." + sub_attr

        self._attr = attr
        self._sub_attr = sub_attr
        self._repr = repr_

    def __repr__(self) -> str:
        return self._repr

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AttrRep):
            return False

        return bool(self._attr == other._attr and self._sub_attr == other._sub_attr)

    def __hash__(self):
        return hash((self._attr, self._sub_attr))

    @property
    def attr(self) -> AttrName:
        return self._attr

    @property
    def sub_attr(self) -> Optional[AttrName]:
        return self._sub_attr

    @property
    def location(self) -> tuple[str, ...]:
        if self._sub_attr:
            return self._attr, self._sub_attr
        return (self._attr,)


class BoundedAttrRep(AttrRep):
    def __init__(
        self,
        schema: str,
        attr: str,
        sub_attr: Optional[str] = None,
    ):
        super().__init__(attr, sub_attr)
        schema = SchemaURI(schema)
        is_extension = schemas.get(schema)
        if is_extension is None:
            raise ValueError(f"unknown schema {schema!r}")

        self._repr = f"{schema}:{self._repr}"
        self._schema = schema
        self._extension = is_extension

    def __eq__(self, other: Any) -> bool:
        parent_equals = super().__eq__(other)
        if not isinstance(other, BoundedAttrRep):
            return parent_equals

        return parent_equals and self._schema == other._schema

    def __hash__(self):
        return hash((self._attr, self._schema, self._sub_attr))

    @property
    def schema(self) -> SchemaURI:
        return self._schema

    @property
    def extension(self) -> bool:
        return self._extension

    @property
    def location(self) -> tuple[str, ...]:
        return ((self._schema,) if self.extension else tuple()) + super().location


class AttrRepFactory:
    @classmethod
    def validate(cls, value: str) -> ValidationIssues:
        issues = ValidationIssues()
        match = _ATTR_REP.fullmatch(value)
        if match is not None:
            schema = match.group(1)
            schema = schema[:-1] if schema else ""
            if not schema or SchemaURI(schema) in schemas:
                return issues
        issues.add_error(
            issue=ValidationError.bad_attribute_name(value),
            proceed=False,
        )
        return issues

    @classmethod
    def deserialize(cls, value: str) -> Union[AttrRep, BoundedAttrRep]:
        try:
            return cls._deserialize(value)
        except Exception as e:
            raise ValueError(f"{value!r} is not valid attribute representation") from e

    @classmethod
    def _deserialize(cls, value: str) -> Union[AttrRep, BoundedAttrRep]:
        if isinstance(value, AttrName):
            return AttrRep(attr=value)

        match = _ATTR_REP.fullmatch(value)
        schema, attr = match.group(1), match.group(2)
        schema = schema[:-1] if schema else ""
        if "." in attr:
            attr, sub_attr = attr.split(".")
        else:
            attr, sub_attr = attr, None
        if schema:
            return BoundedAttrRep(
                schema=schema,
                attr=attr,
                sub_attr=sub_attr,
            )
        return AttrRep(attr=attr, sub_attr=sub_attr)


class InvalidType:
    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Invalid"


Invalid = InvalidType()


class MissingType:
    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Missing"


Missing = MissingType()


@dataclass
class _ContainerKey:
    schema: Optional[str] = None
    extension: bool = False
    attr: Optional[str] = None
    sub_attr: Optional[str] = None


class SCIMDataContainer:
    def __init__(self, d: Optional[Union[dict, "SCIMDataContainer"]] = None):
        self._data = {}
        self._lower_case_to_original = {}

        if isinstance(d, dict):
            for key, value in (d or {}).items():
                if not isinstance(key, str):
                    continue

                self._data.pop(self._lower_case_to_original.get(key.lower()), None)
                self._lower_case_to_original[key.lower()] = key
                if isinstance(value, dict):
                    self._data[key] = SCIMDataContainer(value)
                elif isinstance(value, list):
                    self._data[key] = [
                        SCIMDataContainer(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    self._data[key] = value
        elif isinstance(d, SCIMDataContainer):
            self._data = d._data
            self._lower_case_to_original = d._lower_case_to_original

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self._data)})"

    def set(
        self,
        key: Union[str, SchemaURI, AttrName, AttrRep, BoundedAttrRep, _ContainerKey],
        value: Any,
        expand: bool = False,
    ) -> None:
        key = self._normalize(key)

        if key.schema and not key.attr:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                extension = key.schema
                self._lower_case_to_original[key.schema.lower()] = key.schema
            self._data[extension] = value
            return

        if key.extension:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                extension = key.schema
                self._lower_case_to_original[key.schema.lower()] = extension
                self._data[extension] = SCIMDataContainer()
            self._data[extension].set(
                _ContainerKey(
                    schema=key.schema,
                    attr=key.attr,
                    sub_attr=key.sub_attr,
                ),
                value,
                expand,
            )
            return

        if not key.sub_attr:
            self._data.pop(self._lower_case_to_original.get(key.attr.lower()), None)
            self._lower_case_to_original[key.attr.lower()] = key.attr
            self._data[key.attr] = value
            return

        parent_attr_key = self._lower_case_to_original.get(key.attr.lower())
        if parent_attr_key is None:
            parent_attr_key = key.attr
            self._lower_case_to_original[parent_attr_key.lower()] = parent_attr_key
            if isinstance(value, list) and expand:
                self._data[parent_attr_key] = []
            else:
                self._data[parent_attr_key] = SCIMDataContainer()

        parent_value = self._data[self._lower_case_to_original[parent_attr_key.lower()]]
        if not self._is_child_value_compatible(parent_value, value, expand):
            raise KeyError(f"can not assign ({key.sub_attr}, {value}) to '{key.attr}'")

        if not isinstance(value, list):
            self._data[parent_attr_key].set(_ContainerKey(attr=key.sub_attr), value)
            return

        if expand:
            to_create = len(value) - len(self._data[parent_attr_key])
            if to_create > 0:
                self._data[parent_attr_key].extend([SCIMDataContainer() for _ in range(to_create)])
            for item, container in zip(value, self._data[parent_attr_key]):
                if item is not Missing:
                    container.set(_ContainerKey(attr=key.sub_attr), item)
            return
        self._data[parent_attr_key].set(_ContainerKey(attr=key.sub_attr), value)

    def get(self, key: Union[str, SchemaURI, AttrName, AttrRep, BoundedAttrRep, _ContainerKey]):
        key = self._normalize(key)

        if key.schema and not key.attr:
            extension = self._lower_case_to_original.get(key.schema.lower())
            return self._data.get(extension, Missing)

        extension = self._lower_case_to_original.get(key.schema.lower()) if key.schema else None
        if extension is not None:
            return self._data[extension].get(_ContainerKey(attr=key.attr, sub_attr=key.sub_attr))

        attr = self._lower_case_to_original.get(key.attr.lower())
        if attr is None:
            return Missing

        if key.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value.get(_ContainerKey(attr=key.sub_attr))
            if isinstance(attr_value, list):
                return [
                    item.get(_ContainerKey(attr=key.sub_attr))
                    if isinstance(item, SCIMDataContainer)
                    else Missing
                    for item in attr_value
                ]
            return Missing
        return self._data[attr]

    def pop(self, key: Union[str, SchemaURI, AttrName, AttrRep, BoundedAttrRep, _ContainerKey]):
        key = self._normalize(key)

        if key.schema and not key.attr:
            extension = self._lower_case_to_original.get(key.schema.lower())
            return self._data.pop(extension, Missing)

        extension = self._lower_case_to_original.get(key.schema.lower()) if key.schema else None
        if extension is not None:
            return self._data[extension].pop(_ContainerKey(attr=key.attr, sub_attr=key.sub_attr))

        attr = self._lower_case_to_original.get(key.attr.lower())
        if attr is None:
            return Missing

        if key.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value.pop(key.sub_attr)
            elif isinstance(attr_value, list):
                return [
                    item.pop(key.sub_attr) if isinstance(item, SCIMDataContainer) else Missing
                    for item in attr_value
                ]
            return Missing

        self._lower_case_to_original.pop(key.attr.lower())
        return self._data.pop(attr)

    @staticmethod
    def _normalize(value) -> _ContainerKey:
        if isinstance(value, _ContainerKey):
            return value

        if isinstance(value, SchemaURI):
            return _ContainerKey(schema=str(value))

        if isinstance(value, str):
            try:
                value = SchemaURI(value)
                if value in schemas:
                    return _ContainerKey(schema=str(value))
            except ValueError:
                pass
            value = AttrRepFactory.deserialize(value)

        if isinstance(value, BoundedAttrRep):
            return _ContainerKey(
                schema=str(value.schema),
                attr=str(value.attr),
                sub_attr=value.sub_attr if value.sub_attr else None,
                extension=value.extension,
            )
        return _ContainerKey(
            attr=str(value.attr),
            sub_attr=str(value.sub_attr) if value.sub_attr else None,
        )

    @staticmethod
    def _is_child_value_compatible(
        parent_value: Any,
        child_value: Any,
        expand: True,
    ) -> bool:
        if isinstance(parent_value, list):
            if not isinstance(child_value, list):
                return False
            return True

        if not isinstance(parent_value, SCIMDataContainer):
            return False

        if isinstance(child_value, list) and expand:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        output = {}
        for key, value in self._data.items():
            if isinstance(value, SCIMDataContainer):
                output[key] = value.to_dict()
            elif isinstance(value, list):
                value_output = []
                for item in value:
                    if isinstance(item, SCIMDataContainer):
                        value_output.append(item.to_dict())
                    elif isinstance(item, dict):
                        value_output.append(
                            {
                                k: v.to_dict() if isinstance(v, SCIMDataContainer) else v
                                for k, v in item.items()
                            }
                        )
                    else:
                        value_output.append(item)
                output[key] = value_output
            else:
                output[key] = value
        return output

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            other = SCIMDataContainer(other)
        elif not isinstance(other, SCIMDataContainer):
            return False

        if len(self._data) != len(other._data):
            return False

        for key, value in self._data.items():
            if other.get(key) == value:
                continue

            return other.get(SchemaURI(key)) == value

        return True

    def __bool__(self):
        return bool(self._data)
