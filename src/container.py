import re
from typing import Any, Dict, List, Optional, Union

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

    def top_level_equals(self, other: "BoundedAttrRep") -> bool:
        if all([self.schema, other.schema]):
            return self.attr_with_schema.lower() == other.attr_with_schema.lower()
        return self.attr.lower() == other.attr.lower()


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
    def __init__(self, d: Optional[Union[Dict, "SCIMDataContainer"]] = None):
        self._data = {}
        self._lower_case_to_original = {}

        if isinstance(d, dict):
            for key, value in (d or {}).items():
                if not isinstance(key, str):
                    continue

                self._lower_case_to_original[key.lower()] = key
                if isinstance(value, Dict):
                    self._data[key] = SCIMDataContainer(value)
                elif isinstance(value, List):
                    self._data[key] = [
                        SCIMDataContainer(item) if isinstance(item, Dict) else item
                        for item in value
                    ]
                else:
                    self._data[key] = value
        elif isinstance(d, SCIMDataContainer):
            self._data = d._data
            self._lower_case_to_original = d._lower_case_to_original

    def __repr__(self):
        return str(self._data)

    def set(self, attr_rep: Union[AttrRep, BoundedAttrRep, str], value):
        attr_rep = self._normalize(attr_rep)
        if attr_rep.extension:
            extension_key = self._lower_case_to_original.get(attr_rep.schema.lower())
            if extension_key is None:
                self._lower_case_to_original[attr_rep.schema.lower()] = attr_rep.schema
                self._data[attr_rep.schema] = SCIMDataContainer()
            self._data[attr_rep.schema].set(
                BoundedAttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr), value
            )
        elif attr_rep.sub_attr:
            initial_key = self._lower_case_to_original.get(attr_rep.attr.lower())
            if initial_key is None:
                initial_key = attr_rep.attr
                self._lower_case_to_original[initial_key.lower()] = initial_key
                if isinstance(value, List):
                    self._data[initial_key] = []
                else:
                    self._data[initial_key] = SCIMDataContainer()
            elif not self._can_assign_to_complex(self._data[initial_key], value):
                raise KeyError(
                    f"can not assign ({attr_rep.sub_attr}, {value}) to '{attr_rep.attr}'"
                )
            if isinstance(value, List):
                to_create = len(value) - len(self._data[initial_key])
                if to_create > 0:
                    self._data[initial_key].extend([SCIMDataContainer() for _ in range(to_create)])
                for item, container in zip(value, self._data[initial_key]):
                    if item is not Missing:
                        container.set(BoundedAttrRep(attr=attr_rep.sub_attr), item)
            else:
                self._data[initial_key].set(BoundedAttrRep(attr=attr_rep.sub_attr), value)
        else:
            self._lower_case_to_original[attr_rep.attr.lower()] = attr_rep.attr
            self._data[attr_rep.attr] = value

    def get(self, attr_rep: Union[AttrRep, BoundedAttrRep, str]):
        attr_rep = self._normalize(attr_rep)
        extension = self._lower_case_to_original.get(attr_rep.schema.lower())
        if extension is not None:
            return self._data[extension].get(
                BoundedAttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr)
            )

        attr = self._lower_case_to_original.get(attr_rep.attr.lower())
        if attr is None:
            return Missing

        if attr_rep.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value.get(BoundedAttrRep(attr=attr_rep.sub_attr))
            if isinstance(attr_value, List):
                return [item.get(BoundedAttrRep(attr=attr_rep.sub_attr)) for item in attr_value]
            return Missing
        return self._data[attr]

    def pop(self, attr_rep: Union[AttrRep, BoundedAttrRep, str]):
        attr_rep = self._normalize(attr_rep)
        extension = self._lower_case_to_original.get(attr_rep.schema.lower())
        if extension is not None:
            return self._data[extension].pop(
                BoundedAttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr)
            )

        attr = self._lower_case_to_original.get(attr_rep.attr.lower())
        if attr is None:
            return None

        if attr_rep.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value.pop(attr_rep.sub_attr)
            elif isinstance(attr_value, List):
                return [item.pop(attr_rep.sub_attr) for item in attr_value]
            return None

        self._lower_case_to_original.pop(attr_rep.attr.lower())
        return self._data.pop(attr)

    @staticmethod
    def _normalize(attr_rep) -> BoundedAttrRep:
        if isinstance(attr_rep, str):
            return BoundedAttrRep.deserialize(attr_rep)
        if isinstance(attr_rep, AttrRep):
            return BoundedAttrRep(attr=attr_rep.attr)
        return attr_rep

    @staticmethod
    def _can_assign_to_complex(current_value, new_value) -> bool:
        if isinstance(current_value, SCIMDataContainer):
            return True

        if isinstance(new_value, List) and isinstance(current_value, List):
            current_item_type = {type(item) for item in current_value}
            if current_item_type == {SCIMDataContainer}:
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        output = {}
        for key, value in self._data.items():
            if isinstance(value, SCIMDataContainer):
                output[key] = value.to_dict()
            elif isinstance(value, List):
                value_output = []
                for item in value:
                    if isinstance(item, SCIMDataContainer):
                        value_output.append(item.to_dict())
                    elif isinstance(item, Dict):
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
        if isinstance(other, Dict):
            other = SCIMDataContainer(other)
        elif not isinstance(other, SCIMDataContainer):
            return False

        for key, value in self._data.items():
            if other.get(key) != value:
                return False

        return True
