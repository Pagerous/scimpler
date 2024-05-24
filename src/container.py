import re
from typing import Any, Optional, Union

from src.error import ValidationError, ValidationIssues

_ATTR_NAME = re.compile(r"([a-zA-Z][\w$-]*|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_ATTR_REP = re.compile(
    rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.([a-zA-Z][\w$-]*|\$ref))?)"
)


class AttrRep:
    def __init__(self, attr: str):
        if not _ATTR_NAME.fullmatch(attr):
            raise ValueError(f"{attr!r} is not valid attr name")

        self._attr = attr
        self._repr = attr

    def __repr__(self) -> str:
        return self._repr

    def __eq__(self, other):
        if not isinstance(other, AttrRep):
            return False

        return self.attr.lower() == other.attr.lower()

    @classmethod
    def validate(cls, attr_rep: str) -> ValidationIssues:
        issues = ValidationIssues()
        match = _ATTR_NAME.fullmatch(attr_rep)
        if not match:
            issues.add_error(
                issue=ValidationError.bad_attribute_name(attr_rep),
                proceed=False,
            )
        return issues

    @property
    def attr(self) -> str:
        return self._attr


class BoundedAttrRep:
    def __init__(
        self,
        schema: str = "",
        attr: str = "",
        sub_attr: str = "",
        extension: bool = False,
        extension_required: Optional[bool] = None,
    ):
        if not _ATTR_NAME.fullmatch(attr):
            raise ValueError(f"{attr!r} is not valid attr name")

        attr_ = attr
        if schema:
            attr_ = f"{schema}:{attr_}"
        if sub_attr:
            attr_ += "." + sub_attr

        if not _ATTR_REP.fullmatch(attr_):
            raise ValueError(f"{attr_!r} is not valid attr / sub-attr name")

        if extension and not schema:
            raise ValueError("schema required for attribute from extension")

        self._schema = schema
        self._attr = attr
        self._sub_attr = sub_attr
        self._repr = attr_
        self._extension = extension
        self._extension_required = extension_required

    def __repr__(self) -> str:
        return self._repr

    def __eq__(self, other):
        if not isinstance(other, BoundedAttrRep):
            return False

        if self.attr.lower() != other.attr.lower():
            return False

        if all([self.schema, other.schema]) and self.schema.lower() != other.schema.lower():
            return False

        if self.sub_attr.lower() != other.sub_attr.lower():
            return False

        return True

    @classmethod
    def validate(cls, attr_rep: str) -> ValidationIssues:
        issues = ValidationIssues()
        match = _ATTR_REP.fullmatch(attr_rep)
        if not match:
            issues.add_error(
                issue=ValidationError.bad_attribute_name(attr_rep),
                proceed=False,
            )
        return issues

    @classmethod
    def deserialize(cls, attr_rep: str) -> "BoundedAttrRep":
        try:
            return cls._deserialize(attr_rep)
        except Exception:
            raise ValueError(f"{attr_rep!r} is not valid attribute representation")

    @classmethod
    def _deserialize(cls, attr_rep: str) -> "BoundedAttrRep":
        match = _ATTR_REP.fullmatch(attr_rep)
        schema, attr = match.group(1), match.group(2)
        schema = schema[:-1] if schema else ""
        if "." in attr:
            attr, sub_attr = attr.split(".")
        else:
            attr, sub_attr = attr, ""
        return BoundedAttrRep(schema=schema, attr=attr, sub_attr=sub_attr)

    @property
    def extension(self) -> bool:
        return self._extension

    @property
    def extension_required(self) -> Optional[bool]:
        return self._extension_required

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attr(self) -> str:
        return self._attr

    @property
    def attr_with_schema(self) -> str:
        if self.schema:
            return f"{self.schema}:{self.attr}"
        return self.attr

    @property
    def sub_attr(self) -> str:
        return self._sub_attr

    def parent_equals(self, other: "BoundedAttrRep") -> bool:
        if all([self.schema, other.schema]):
            return self.attr_with_schema.lower() == other.attr_with_schema.lower()
        return self.attr.lower() == other.attr.lower()


class SchemaURI(str):
    def __new__(cls, value: str):
        if not _URI_PREFIX.fullmatch(value + ":"):
            raise ValueError(f"{value!r} is not a valid schema URI")
        return str.__new__(cls, value)


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
        key: Union[SchemaURI, AttrRep, BoundedAttrRep, str],
        value: Any,
        expand: bool = False,
    ) -> None:
        if isinstance(key, SchemaURI):
            extension = self._lower_case_to_original.get(key.lower())
            if extension is None:
                extension = key
                self._lower_case_to_original[key.lower()] = key
            self._data[extension] = value
            return

        key = self._normalize(key)
        if key.extension:
            extension = self._lower_case_to_original.get(key.schema.lower())
            if extension is None:
                extension = key.schema
                self._lower_case_to_original[key.schema.lower()] = extension
                self._data[extension] = SCIMDataContainer()
            self._data[extension].set(
                BoundedAttrRep(attr=key.attr, sub_attr=key.sub_attr), value, expand
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
            self._data[parent_attr_key].set(BoundedAttrRep(attr=key.sub_attr), value)
            return

        if expand:
            to_create = len(value) - len(self._data[parent_attr_key])
            if to_create > 0:
                self._data[parent_attr_key].extend([SCIMDataContainer() for _ in range(to_create)])
            for item, container in zip(value, self._data[parent_attr_key]):
                if item is not Missing:
                    container.set(BoundedAttrRep(attr=key.sub_attr), item)
            return
        self._data[parent_attr_key].set(BoundedAttrRep(attr=key.sub_attr), value)

    def get(self, key: Union[SchemaURI, AttrRep, BoundedAttrRep, str]):
        if isinstance(key, SchemaURI):
            extension = self._lower_case_to_original.get(key.lower())
            return self._data.get(extension, Missing)

        key = self._normalize(key)
        extension = self._lower_case_to_original.get(key.schema.lower())
        if extension is not None:
            return self._data[extension].get(BoundedAttrRep(attr=key.attr, sub_attr=key.sub_attr))

        attr = self._lower_case_to_original.get(key.attr.lower())
        if attr is None:
            return Missing

        if key.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value.get(BoundedAttrRep(attr=key.sub_attr))
            if isinstance(attr_value, list):
                return [
                    item.get(BoundedAttrRep(attr=key.sub_attr))
                    if isinstance(item, SCIMDataContainer)
                    else Missing
                    for item in attr_value
                ]
            return Missing
        return self._data[attr]

    def pop(self, key: Union[SchemaURI, AttrRep, BoundedAttrRep, str]):
        if isinstance(key, SchemaURI):
            extension = self._lower_case_to_original.get(key.lower())
            return self._data.pop(extension, Missing)

        key = self._normalize(key)
        extension = self._lower_case_to_original.get(key.schema.lower())
        if extension is not None:
            return self._data[extension].pop(BoundedAttrRep(attr=key.attr, sub_attr=key.sub_attr))

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
    def _normalize(attr_rep) -> BoundedAttrRep:
        if isinstance(attr_rep, str):
            return BoundedAttrRep.deserialize(attr_rep)
        if isinstance(attr_rep, AttrRep):
            return BoundedAttrRep(attr=attr_rep.attr)
        return attr_rep

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

        for key, value in self._data.items():
            if other.get(key) == value:
                continue

            return other.get(SchemaURI(key)) == value

        return True

    def __bool__(self):
        return bool(self._data)
