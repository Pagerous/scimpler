from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from scimpler.data.identifiers import AttrRep, AttrRepFactory, BoundedAttrRep, SchemaURI
from scimpler.registry import schemas


class InvalidType:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Invalid"


Invalid = InvalidType()


class MissingType:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Missing"


Missing = MissingType()


@dataclass
class _SchemaKey:
    schema: str


@dataclass
class _AttrKey:
    attr: str
    sub_attr: Optional[str]


@dataclass
class _BoundedAttrKey(_AttrKey):
    schema: str
    extension: bool


class SCIMData(MutableMapping):
class ScimData(MutableMapping):
    def __init__(
        self, d: Optional[Union[Mapping[str, Any], Mapping[AttrRep, Any], "ScimData"]] = None
    ):
        self._data: dict[str, Any] = {}
        self._lower_case_to_original: dict[str, str] = {}

        if isinstance(d, SCIMData):
            self._data = d._data
            self._lower_case_to_original = d._lower_case_to_original
        elif isinstance(d, Mapping):
            for key, value in d.items():
                if isinstance(key, AttrRep):
                    self.set(key, value)

                if not isinstance(key, str):
                    continue

                if original_key := self._lower_case_to_original.get(key.lower()):
                    self._data.pop(original_key, None)
                self._lower_case_to_original[key.lower()] = key
                if isinstance(value, Mapping):
                    self._data[key] = SCIMData(value)
                elif isinstance(value, list):
                    self._data[key] = [
                        SCIMData(item) if isinstance(item, Mapping) else item for item in value
                    ]
                else:
                    self._data[key] = value

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self._data)})"

    def __getitem__(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey]):
        value = self.get(key)
        if value is Missing:
            raise KeyError(key)
        return value

    def __setitem__(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey], value: Any):
        self.set(key, value)

    def __delitem__(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey]):
        value = self.pop(key)
        if value is Missing:
            raise KeyError(key)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def set(
        self,
        key: Union[str, AttrRep, _SchemaKey, _AttrKey],
        value: Any,
    ) -> None:
        if isinstance(value, Mapping):
            value = ScimData(value)
        elif not isinstance(value, str) and isinstance(value, Iterable):
            value = [ScimData(item) if isinstance(item, Mapping) else item for item in value]

        if not isinstance(key, (_SchemaKey, _AttrKey)):
            key = self._normalize(key)

        if isinstance(key, _SchemaKey):
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                extension = key.schema
                self._lower_case_to_original[key.schema.lower()] = key.schema
            self._data[extension] = value
            return

        elif isinstance(key, _BoundedAttrKey) and key.extension:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                extension = key.schema
                self._lower_case_to_original[key.schema.lower()] = extension
                self._data[extension] = ScimData()
            self._data[extension].set(_AttrKey(attr=key.attr, sub_attr=key.sub_attr), value)
            return

        if not key.sub_attr:
            if original_key := self._lower_case_to_original.get(key.attr.lower()):
                self._data.pop(original_key, None)
            self._lower_case_to_original[key.attr.lower()] = key.attr
            self._data[key.attr] = value
            return

        parent_attr_key = self._lower_case_to_original.get(key.attr.lower())
        if parent_attr_key is None:
            parent_attr_key = key.attr
            self._lower_case_to_original[parent_attr_key.lower()] = parent_attr_key
            self._data[parent_attr_key] = ScimData()

        parent_value = self._data[self._lower_case_to_original[parent_attr_key.lower()]]
        if not self._is_child_value_compatible(parent_value, value):
            raise KeyError(f"can not assign ({key.sub_attr}, {value}) to '{key.attr}'")

        if not isinstance(value, list):
            self._data[parent_attr_key].set(_AttrKey(attr=key.sub_attr, sub_attr=None), value)
            return

        self._data[parent_attr_key].set(_AttrKey(attr=key.sub_attr, sub_attr=None), value)

    def get(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey], default: Any = Missing) -> Any:
        if not isinstance(key, (_SchemaKey, _AttrKey)):
            key = self._normalize(key)

        if isinstance(key, _SchemaKey):
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                return default
            return self._data.get(extension, default)

        if isinstance(key, _BoundedAttrKey) and key.extension:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                return default
            return self._data[extension].get(_AttrKey(attr=key.attr, sub_attr=key.sub_attr))

        attr = self._lower_case_to_original.get(key.attr.lower())
        if attr is None:
            return default

        if key.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, ScimData):
                return attr_value.get(_AttrKey(attr=key.sub_attr, sub_attr=None))
            if isinstance(attr_value, list):
                return [
                    item.get(_AttrKey(attr=key.sub_attr, sub_attr=None))
                    if isinstance(item, ScimData)
                    else default
                    for item in attr_value
                ]
            return default
        return self._data.get(attr, default)

    def pop(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey], default: Any = Missing) -> Any:
        if not isinstance(key, (_SchemaKey, _AttrKey)):
            key = self._normalize(key)

        if isinstance(key, _SchemaKey):
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                return default
            return self._data.pop(extension, default)

        elif isinstance(key, _BoundedAttrKey) and key.extension:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                return default
            return self._data[extension].pop(
                _AttrKey(attr=key.attr, sub_attr=key.sub_attr), default
            )

        attr = self._lower_case_to_original.get(key.attr.lower())
        if attr is None:
            return default

        if key.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, ScimData):
                return attr_value.pop(key.sub_attr, default)
            elif isinstance(attr_value, list):
                return [
                    item.pop(key.sub_attr, default) if isinstance(item, ScimData) else default
                    for item in attr_value
                ]
            return default

        self._lower_case_to_original.pop(key.attr.lower())
        return self._data.pop(attr, default)

    @staticmethod
    def _normalize(value: Union[str, AttrRep]) -> Union[_SchemaKey, _AttrKey]:
        if isinstance(value, SchemaURI):
            if schemas.get(value, False) is False:
                raise KeyError(
                    f"schema {value!r} is not recognized or is an extension, so does not require "
                    "own subspace in the data"
                )
            return _SchemaKey(schema=str(value))

        if isinstance(value, str):
            try:
                value = SchemaURI(value)
                is_extension = schemas.get(value)
                if is_extension is False:
                    raise KeyError(
                        f"schema {value!r} is an extension, so does not require "
                        "own subspace in the data"
                    )
                elif is_extension is True:
                    return _SchemaKey(schema=str(value))
            except ValueError:
                pass
            value = AttrRepFactory.deserialize(value)

        if isinstance(value, BoundedAttrRep):
            return _BoundedAttrKey(
                schema=str(value.schema),
                attr=str(value.attr),
                sub_attr=value.sub_attr if value.is_sub_attr else None,
                extension=value.extension,
            )
        return _AttrKey(
            attr=str(value.attr),
            sub_attr=str(value.sub_attr) if value.is_sub_attr else None,
        )

    @staticmethod
    def _is_child_value_compatible(
        parent_value: Any,
        child_value: Any,
    ) -> bool:
        if isinstance(parent_value, list):
            if not isinstance(child_value, list):
                return False
            return True

        if not isinstance(parent_value, ScimData):
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in self._data.items():
            if isinstance(value, ScimData):
                output[key] = value.to_dict()
            elif isinstance(value, list):
                value_output = []
                for item in value:
                    if isinstance(item, ScimData):
                        value_output.append(item.to_dict())
                    else:
                        value_output.append(item)
                output[key] = value_output
            else:
                output[key] = value
        return output

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Mapping):
            other = ScimData(other)

        if not isinstance(other, ScimData):
            return False

        if len(self) != len(other):
            return False

        for key, value in self._data.items():
            if other.get(key) != value:
                return False

        return True
