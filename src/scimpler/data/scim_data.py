from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from scimpler.data.identifiers import AttrRep, AttrRepFactory, BoundedAttrRep, SchemaUri
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


class ScimData(MutableMapping):
    """
    Mapping that implements reading and updating data which is in line with SCIM requirements.
    Enables convenient interaction, where keys are just attribute representations, and abstracts
    all inner complexities.

    According to SCIM requirements, complex attributes can not contain nested complex attributes
    (it is general rule, but there are exceptions). It would mean the 2-level nesting should be
    enough (or 3, for data from extensions), but `ScimData` has no such limitation. Every nesting
    level has no awareness of its parent key.
    """

    def __init__(
        self, d: Optional[Union[Mapping[str, Any], Mapping[AttrRep, Any], "ScimData"]] = None
    ):
        """
        Args:
            d: Optional data to initialize `ScimData` with. Can be any mapping that has keys of
                type of `str`, `AttrRep`, or `BoundedAttrRep`. Every key with other type is
                ignored.

        Examples:
            >>> ScimData({"myAttr": "value", "myOtherAttr": {"mySubAttr": 42}}).to_dict()
            {"myAttr": "value", "myOtherAttr": {"mySubAttr": 42}}

            >>> ScimData(
            >>>     {
            >>>         AttrRep(attr="myAttr"): "value",
            >>>         AttrRep(attr="myOtherAttr", sub_attr="mySubAttr"): 42
            >>>     }
            >>> ).to_dict()
            {"myAttr": "value", "myOtherAttr": {"mySubAttr": 42}}

            >>> from scimpler.schemas import UserSchema
            >>>
            >>> user = UserSchema()
            >>> ScimData(
            >>>     {user.attrs.name__formatted: "John Doe", user.attrs.externalId: "42"}
            >>> ).to_dict()
            {"name": {"formatted": "John Doe"}, "externalId": "42"}
        """
        self._data: dict[str, Any] = {}
        self._lower_case_to_original: dict[str, str] = {}

        if isinstance(d, ScimData):
            self._data = d._data
            self._lower_case_to_original = d._lower_case_to_original
        elif isinstance(d, Mapping):
            for key, value in d.items():
                if not isinstance(key, (str, AttrRep)):
                    continue
                self.set(key, value)

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
        """
        Sets the entry in the mapping. Equivalent to `data[key] = value`. The way how the
        value is actually set depends on the type of `key`:

        - if `str` is provided, the key is parsed to one of supported key types and used as follows,
        - if `SchemaUri` representing schema extension is provided, the `value` is set directly
            under the key,
        - if `SchemaUri` representing base schema is provided, a `ValueError` exception is raised,
        - if `AttrRep` is provided, the `value` is set directly under the key, if `key` represents
            top-level attribute, or it is nested under `AttrRep.sub_attr`, if it represents
            a sub-attribute,
        - if `BoundedAttrRep` is provided, the `value` is set in the same way as for `AttrRep`
            for attributes that belong to base schemas. For attributes from extensions,
            the value is additionally nested in schema URI key namespace.


        Raises:
            ValueError: If `key` is `SchemaUri` reprensenting base schema.
            KeyError: If trying to set sub-attribute value to existing parent that is
                not single-valued complex attribute value.

        Args:
            key: The key for which the `value` should be set.
            value: The value to be set.

        Examples:
            >>> data = ScimData()
            >>> data.set("userName", "johndoe")
            >>> data.to_dict()
            {"userName": "johndoe"}

            >>> data = ScimData()
            >>> data.set("name.formatted", "John Doe")
            >>> data.to_dict()
            {"name": {"formatted": "John Doe"}}

            >>> data = ScimData()
            >>> data.set(
            >>>     "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted", "John Doe"
            >>> )
            >>> data.to_dict()
            {"name": {"formatted": "John Doe"}}

            >>> data = ScimData()
            >>> data.set(
            >>>     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            >>>     {
            >>>         "employeeNumber": "42",
            >>>         "manager": {"displayName": "John Doe"}
            >>>     }
            >>> )
            >>> data.to_dict()
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "42"
                    "manager": {
                        "displayName": "John Doe"
                    }
                }
            }

            >>> data = ScimData()
            >>> data.set(
            >>>     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            >>>     ":manager.value",
            >>>     "10",
            >>> )
            >>> data.to_dict()
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "manager": {
                        "value": "10"
                    }
                }
            }
        """
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
        if not isinstance(parent_value, ScimData):
            raise KeyError(f"can not assign ({key.sub_attr}, {value}) to '{key.attr}'")

        self._data[parent_attr_key].set(_AttrKey(attr=key.sub_attr, sub_attr=None), value)

    def get(self, key: Union[str, AttrRep, _SchemaKey, _AttrKey], default: Any = Missing) -> Any:
        """
        Returns the value for the specified `key`. If not found, the specified `default`
        is returned (`Missing` object by default).

        The type of `key` determines which entry is actually accessed:
        - if `str` is provided, the key is parsed to one of supported key types and used as follows,
        - if `SchemaUri` representing schema extension is provided, the whole subsection that
            belongs to it is returned,
        - if `SchemaUri` representing base schema is provided, a `ValueError` exception is raised,
        - if `AttrRep` is provided, the retrieved value belongs to top-level attribute, or nested
            one, kept under `AttrRep.sub_attr`, if `key` represents a sub-attribute,
        - if `BoundedAttrRep` is provided, the value is retrieved in the same way as for `AttrRep`
            for attributes that belong to base schemas. For attributes from extensions,
            the value is retrieved from schema URI key namespace.

        Raises:
            ValueError: If `key` is `SchemaUri` reprensenting base schema.
            KeyError: If trying to set sub-attribute value to existing parent that is
                not single-valued complex attribute value.

        Args:
            key: The key for which the value should be retrieved.
            default: The default value, if value for the `key` is not found.

        Examples:
            >>> data = ScimData(
            >>>     {
            >>>         "userName": "Pagerous",
            >>>         "name": {"formatted": "AP"},
            >>>         "emails": [
            >>>             {"type": "work", "value": "..."}, {"type": "home", "value": "..."}
            >>>         ],
            >>>         "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            >>>             "employeeNumber": "42",
            >>>             "manager": {
            >>>                 "displayName": "John Doe"
            >>>             }
            >>>         }
            >>>     }
            >>> )
            >>> data.get("userName")
            "Pagerous"
            >>> data.get("name")
            "{"formatted": "AP"}"
            >>> data.get("name.formatted")
            "AP"
            >>> data.get("urn:ietf:params:scim:schemas:core:2.0:User:name.formatted")
            "AP"
            >>> data.get("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "42"
                    "manager": {
                        "displayName": "John Doe"
                    }
                }
            }
            >>> data.get(
            >>>     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            >>>     ":employeeNumber"
            >>> )
            "42"
            >>> data.get(
            >>>     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            >>>     ":manager.displayName"
            >>> )
            "John Doe"
            >>> data.get("emails.type")
            ["work", "home"]
            >>> data.get("unknown")
            Missing
        """
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
        """
        Pops the `key` from the data. Works similarly to `get` with the difference that after
        returning the value, it is not available in the data any longer.
        """

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
        if isinstance(value, SchemaUri):
            if schemas.get(value, False) is False:
                raise KeyError(
                    f"schema {value!r} is not recognized or is an extension, so does not require "
                    "own namespace in the data"
                )
            return _SchemaKey(schema=str(value))

        if isinstance(value, str):
            try:
                value = SchemaUri(value)
                is_extension = schemas.get(value)
                if is_extension is False:
                    raise KeyError(
                        f"schema {value!r} is an extension, so does not require "
                        "own namespace in the data"
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

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the `ScimData` to ordinary dictionary.
        """
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
