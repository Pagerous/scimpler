import functools
import typing
from collections.abc import MutableMapping
from typing import Any, Iterable, Optional, Sequence, Union

from scimpler.data import AttrRepFactory, BoundedAttrRep
from scimpler.data.attrs import Attribute, AttributeWithCaseExact, Complex, String
from scimpler.data.schemas import BaseResourceSchema
from scimpler.data.scim_data import AttrRep, Invalid, Missing, ScimData


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

        value = self._value
        other_value = other._value

        if isinstance(self._attr, String):
            value = self._attr.precis.enforce(value)
        if isinstance(other._attr, String):
            other_value = other._attr.precis.enforce(other_value)

        if (
            isinstance(self._attr, AttributeWithCaseExact)
            and self._attr.case_exact
            or isinstance(other._attr, AttributeWithCaseExact)
            and other._attr.case_exact
        ):
            return value < other_value

        return value.lower() < other_value.lower()


class Sorter:
    """
    Sorter implementing sorting logic, as specified in RFC-7644.
    """

    def __init__(self, attr_rep: Union[str, AttrRep], asc: bool = True):
        """
        Args:
            attr_rep: The representation of the attribute by which the data should be sorted.
            asc: If set to `True`, it enables ascending sorting. Descending otherwise.
        """
        self._attr_rep = (
            attr_rep if isinstance(attr_rep, AttrRep) else AttrRepFactory.deserialize(attr_rep)
        )
        self._asc = asc
        self._default_value = AlwaysLastKey()

    @property
    def attr_rep(self) -> AttrRep:
        """
        The representation of the attribute by which the data should be sorted.
        """
        return self._attr_rep

    @property
    def asc(self) -> bool:
        """
        If `True`, ascending sorting is enabled. Descending otherwise.
        """
        return self._asc

    def bind(self, schema: BaseResourceSchema) -> "Sorter":
        if isinstance(self._attr_rep, BoundedAttrRep) and self._attr_rep.schema != schema.schema:
            raise ValueError(
                f"can not bind sorter to schema {schema.schema} because its attribute "
                f"representation is bound to {self._attr_rep.schema}"
            )

        return Sorter(
            attr_rep=BoundedAttrRep(
                schema=schema.schema,
                attr=self._attr_rep.attr,
                sub_attr=self._attr_rep.sub_attr if self._attr_rep.is_sub_attr else None,
            ),
            asc=self._asc,
        )

    def __call__(
        self,
        data: Iterable[MutableMapping],
        schema: Union[BaseResourceSchema, Sequence[BaseResourceSchema]],
    ) -> list[ScimData]:
        """
        Sorts the provided data according to the sorter configuration and the provided schemas.
        It is able to perform sorting of data items that belong to the same schema, or to different
        schemas (e.g. `UserSchema` and `GroupSchema`).

        Sorting is performed in line with value types semantics. For "string" attributes,
        case-sensitivity and PRECIS profile is respected.

        If the data item misses the attribute the data is sorted by, it is ordered last
        (if ascending sorting).

        A multi-valued complex attribute is sorted by the value of "primary" item, if it defines
        `value` and `primary` attribtues. If `primary` is not defined, or it is not contained in
        the data, the first `value` is used for sorting.

        Args:
            data: The data to sort.
            schema: Schema or schemas that describe the data. If single schema is passed, it is
                assumed all data described by the same schema. If passed multiple schemas,
                for every data item must be provided corresponding schema.

        Returns:
            Sorted data.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>> from scimpler.data.identifiers import AttrRep
            >>>
            >>> sorter = Sorter(attr_rep=AttrRep("userName"), asc=False)
            >>> sorter(
            >>>     [{"userName": "a_user"}, {"userName": "b_user"}], UserSchema()
            >>> )
            >>> [{"userName": "b_user"}, {"userName": "a_user"}]

            >>> from scimpler.schemas import GroupSchema, UserSchema
            >>> from scimpler.data.identifiers import AttrRep
            >>>
            >>> group, user = GroupSchema(), UserSchema()
            >>> sorter = Sorter(attr_rep=AttrRep("externalId"), asc=True)
            >>> sorter(
            >>>     [{"externalId": "2"}, {"externalId": "1"}, {"externalId": "3"}],
            >>>     [user, group, user],
            >>> )
            >>> [{"externalId": "1"}, {"externalId": "2"}, {"externalId": "3"}]

        """
        normalized = [ScimData(item) for item in data]
        if not normalized:
            return normalized
        return self._sort(normalized, schema)

    def _sort(
        self,
        data: list[ScimData],
        schema: Union[BaseResourceSchema, Sequence[BaseResourceSchema]],
    ) -> list[ScimData]:
        if not any(item.get(self._attr_rep) for item in data):
            return data

        if not isinstance(schema, BaseResourceSchema) and len(set(schema)) == 1:
            schema = schema[0]
        if isinstance(schema, BaseResourceSchema):
            key = functools.partial(self._attr_key, schema=schema)
        else:
            key = self._attr_key_many_schemas(data, schema)
        return sorted(data, key=key, reverse=not self._asc)

    def _get_key(self, value: Any, attr: Optional[Attribute]):
        if value in [None, Missing, "", Invalid] or attr is None:
            return self._default_value

        if not isinstance(value, str):
            return value

        if str not in attr.base_types:
            return self._default_value

        return StringKey(value, attr)

    def _attr_key_many_schemas(self, data: list[ScimData], schemas: Sequence[BaseResourceSchema]):
        def attr_key(item):
            schema = schemas[data.index(item)]
            return self._attr_key(item, schema)

        return attr_key

    def _attr_key(self, item: ScimData, schema: BaseResourceSchema):
        attr = schema.attrs.get(self._attr_rep)
        if attr is None:
            return self._get_key(None, None)

        if self._attr_rep.is_sub_attr:
            return self._get_sub_attr_key(item, schema, attr)
        return self._get_attr_key(item, attr)

    def _get_sub_attr_key(self, item: ScimData, schema: BaseResourceSchema, attr: Attribute):
        top_level_attr_rep = self._attr_rep.create_attr_rep()
        top_level_attr = typing.cast(Complex, schema.attrs.get(top_level_attr_rep))
        top_level_attr_value = item.get(top_level_attr_rep)
        if not top_level_attr_value:
            return self._get_key(None, attr)

        value = None
        if top_level_attr.multi_valued:
            for i, v in enumerate(top_level_attr_value):
                if i == 0:
                    value = v.get(self._attr_rep.sub_attr)
                elif v.get("primary") is True:
                    value = v.get(self._attr_rep.sub_attr)
                    break
        else:
            value = top_level_attr_value.get(self._attr_rep.sub_attr)

        if value and attr.multi_valued:
            value = value[0]

        return self._get_key(value, attr)

    def _get_attr_key(self, item: ScimData, attr: Attribute):
        attr_value = item.get(self._attr_rep)
        if attr_value in [None, Missing, "", Invalid, {}, []]:
            return self._get_key(None, attr)

        value = None
        if isinstance(attr, Complex) and attr.multi_valued:
            for i, v in enumerate(attr_value):
                if i == 0:
                    value = v.get("value")
                elif v.get("primary") is True:
                    value = v.get("value")
                    break
            return self._get_key(value, attr.attrs.get("value"))

        value = attr_value[0] if attr.multi_valued else attr_value
        return self._get_key(value, attr)
