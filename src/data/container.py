import re
from typing import Any, Dict, List, Optional, Tuple, Union

_ATTR_NAME = re.compile(r"(\w+|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_ATTR_REP = re.compile(rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.\w+)?)")


class AttrRep:
    def __init__(
        self, schema: str = "", attr: str = "", sub_attr: str = "", extension: bool = False
    ):
        if not _ATTR_NAME.fullmatch(attr):
            raise ValueError(f"{attr!r} is not valid attr name")

        attr_ = attr
        if schema:
            attr_ = f"{schema}:{attr_}"
        if sub_attr:
            attr_ += "." + sub_attr

        if not _ATTR_REP.fullmatch(attr):
            raise ValueError(f"{attr_!r} is not valid attr / sub-attr name")

        if extension and not schema:
            raise ValueError("schema required for attribute from extension")

        self._schema = schema
        self._attr = attr
        self._sub_attr = sub_attr
        self._repr = attr_
        self._extension = extension

    def __repr__(self) -> str:
        return self._repr

    def __eq__(self, other):
        if not isinstance(other, AttrRep):
            return False

        if all([self.schema, other.schema]) and self.schema.lower() != other.schema.lower():
            return False

        if self.attr.lower() != other.attr.lower():
            return False

        if self.sub_attr.lower() != other.sub_attr.lower():
            return False

        return True

    @classmethod
    def parse(cls, attr_rep: str) -> Optional["AttrRep"]:
        match = _ATTR_REP.fullmatch(attr_rep)
        if not match:
            return None

        schema, attr = match.group(1), match.group(2)
        schema = schema[:-1] if schema else ""
        if "." in attr:
            attr, sub_attr = attr.split(".")
        else:
            attr, sub_attr = attr, ""
        return AttrRep(schema=schema, attr=attr, sub_attr=sub_attr)

    @property
    def extension(self) -> bool:
        return self._extension

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attr_with_schema(self) -> str:
        if self.schema:
            return f"{self.schema}:{self.attr}"
        return self.attr

    @property
    def attr(self) -> str:
        return self._attr

    @property
    def sub_attr(self) -> str:
        return self._sub_attr

    def top_level_equals(self, other: "AttrRep") -> bool:
        if all([self.schema, other.schema]):
            return self.attr_with_schema.lower() == other.attr_with_schema.lower()
        return self.attr.lower() == other.attr.lower()


class MissingType:
    def __bool__(self):
        return False

    def __repr__(self):
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

    def __setitem__(self, attr_rep: "AttrRep", value):
        if attr_rep.extension:
            extension_key = self._lower_case_to_original.get(attr_rep.schema.lower())
            if extension_key is None:
                self._lower_case_to_original[attr_rep.schema.lower()] = attr_rep.schema
                self._data[attr_rep.schema] = SCIMDataContainer()
            self._data[attr_rep.schema][
                AttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr)
            ] = value
        elif attr_rep.sub_attr:
            attr_key = self._lower_case_to_original.get(attr_rep.attr.lower())
            if attr_key is None:
                self._lower_case_to_original[attr_rep.attr.lower()] = attr_rep.attr
                if isinstance(value, List):
                    self._data[attr_rep.attr] = []
                else:
                    self._data[attr_rep.attr] = SCIMDataContainer()
            if isinstance(value, List):
                to_create = len(value) - len(self._data[attr_rep.attr])
                if to_create > 0:
                    self._data[attr_rep.attr].extend(
                        [SCIMDataContainer() for _ in range(to_create)]
                    )
                for item, container in zip(value, self._data[attr_rep.attr]):
                    if item is not Missing:
                        container[AttrRep(attr=attr_rep.sub_attr)] = item
            else:
                self._data[attr_rep.attr][AttrRep(attr=attr_rep.sub_attr)] = value
        else:
            self._lower_case_to_original[attr_rep.attr.lower()] = attr_rep.attr
            self._data[attr_rep.attr] = value

    def __getitem__(
        self, attr_rep: Union["AttrRep", str, Tuple[str], Tuple[str, str], Tuple[str, str, str]]
    ):
        if not isinstance(attr_rep, AttrRep):
            attr_rep = self._to_attr_rep(attr_rep)

        extension = self._lower_case_to_original.get(attr_rep.schema.lower())
        if extension is not None:
            return self._data[extension][AttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr)]

        attr = self._lower_case_to_original.get(attr_rep.attr.lower())
        if attr is None:
            return Missing

        if attr_rep.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                return attr_value[AttrRep(attr=attr_rep.sub_attr)]
            if isinstance(attr_value, List):
                return [item[AttrRep(attr=attr_rep.sub_attr)] for item in attr_value]
            return Missing
        return self._data[attr]

    def __delitem__(
        self, attr_rep: Union["AttrRep", str, Tuple[str], Tuple[str, str], Tuple[str, str, str]]
    ):
        if not isinstance(attr_rep, AttrRep):
            attr_rep = self._to_attr_rep(attr_rep)

        extension = self._lower_case_to_original.get(attr_rep.schema.lower())
        if extension is not None:
            del self._data[extension][AttrRep(attr=attr_rep.attr, sub_attr=attr_rep.sub_attr)]
            return

        attr = self._lower_case_to_original.get(attr_rep.attr.lower())
        if attr is None:
            return

        if attr_rep.sub_attr:
            attr_value = self._data[attr]
            if isinstance(attr_value, SCIMDataContainer):
                del attr_value[AttrRep(attr=attr_rep.sub_attr)]
            elif isinstance(attr_value, List):
                for item in attr_value:
                    del item[AttrRep(attr=attr_rep.sub_attr)]
            return

        self._data.pop(attr)
        self._lower_case_to_original.pop(attr_rep.attr.lower())

    @staticmethod
    def _to_attr_rep(attr_rep):
        if isinstance(attr_rep, str):
            if _URI_PREFIX.fullmatch(attr_rep):
                raise ValueError("attribute name is required")
            return AttrRep(attr=attr_rep)

        if len(attr_rep) == 1:
            if _URI_PREFIX.fullmatch(attr_rep[0]):
                raise ValueError("attribute name is required")
            return AttrRep(attr=attr_rep[0])

        if len(attr_rep) == 2:
            if _URI_PREFIX.fullmatch(attr_rep[0]):
                return AttrRep(*attr_rep)
            return AttrRep(attr=attr_rep[0], sub_attr=attr_rep[1])

        return AttrRep(*attr_rep)

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
            if other[key] != value:
                return False

        return True
