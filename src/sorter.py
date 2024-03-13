import functools
from typing import Any, List, Optional, Sequence, Tuple, Union

from src.data import type as at
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema, ResourceSchema
from src.error import ValidationError, ValidationIssues


class AlwaysLastKey:
    def __lt__(self, _):
        return False

    def __gt__(self, _):
        return True


class StringKey:
    def __init__(self, value: str, attr: Attribute):
        self._value = value
        self._attr = attr

    def __lt__(self, other):
        if not isinstance(other, StringKey):
            if isinstance(other, AlwaysLastKey):
                return True
            raise TypeError(
                f"'<' not supported between instances of 'StringKey' and '{type(other).__name__}'"
            )

        if self._attr.case_exact or other._attr.case_exact:
            return self._value < other._value

        return self._value.lower() < other._value.lower()


class Sorter:
    def __init__(self, attr_rep: AttrRep, asc: bool = True):
        self._attr_rep = attr_rep
        self._asc = asc
        self._default_value = AlwaysLastKey()

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep

    @property
    def asc(self) -> bool:
        return self._asc

    @classmethod
    def parse(cls, by: str, asc: bool = True) -> Tuple[Union[Invalid, "Sorter"], ValidationIssues]:
        issues = ValidationIssues()
        attr_rep = AttrRep.parse(by)
        if attr_rep is Invalid:
            issues.add(
                issue=ValidationError.bad_attribute_name(by),
                proceed=False,
            )
            return Invalid, issues
        return (
            Sorter(attr_rep=attr_rep, asc=asc),
            issues,
        )

    def __call__(
        self,
        data: List[SCIMDataContainer],
        schema: Union[ResourceSchema, Sequence[ResourceSchema]],
    ) -> List[SCIMDataContainer]:
        if not any(item[self._attr_rep] for item in data):
            return data

        if not isinstance(schema, ResourceSchema) and len(set(schema)) == 1:
            schema = schema[0]

        if isinstance(schema, ResourceSchema):
            key = functools.partial(self._attr_key, schema=schema)
        else:
            key = self._attr_key_many_schemas(data, schema)

        return sorted(data, key=key, reverse=not self._asc)

    def _get_key(self, value: Any, attr: Optional[Attribute]):
        if not value or attr is None:
            return self._default_value

        if not isinstance(value, str):
            return value

        if attr.type is not at.String:
            return self._default_value

        return StringKey(value, attr)

    def _attr_key_many_schemas(self, data: List[SCIMDataContainer], schemas: Sequence[BaseSchema]):
        def attr_key(item):
            schema = schemas[data.index(item)]
            return self._attr_key(item, schema)

        return attr_key

    def _attr_key(self, item: SCIMDataContainer, schema: BaseSchema):
        attr = schema.attrs.get(self._attr_rep)
        value = None
        if attr is not None:
            item_value = item[self._attr_rep]
            if item_value is not Missing and attr.multi_valued:
                if isinstance(attr, ComplexAttribute):
                    for v in item_value:
                        primary = v["primary"]
                        if primary is True:
                            for sub_attr in attr.attrs:
                                if sub_attr.rep.attr.lower() == "value":
                                    attr = sub_attr
                                    break
                            else:
                                attr = None
                            value = v["value"]
                            break
                else:
                    value = item_value[0]
            else:
                value = item_value
        return self._get_key(value, attr)
