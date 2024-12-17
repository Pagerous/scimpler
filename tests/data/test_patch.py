import pytest

from scimpler.data import PatchOperations
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep
from scimpler.data.operator import ComplexAttributeOperator, Equal
from scimpler.data.patch import (
    Add,
    MutabilityException,
    NoTargetException,
    PatchPath,
    Remove,
    Replace,
)
from scimpler.data.schemas import ResourceSchema


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        ("bad^attr", {"_errors": [{"code": 17, "context": {"attribute": "bad^attr"}}]}),
        (
            "good_attr.bad^sub_attr",
            {"_errors": [{"code": 17, "context": {"attribute": "good_attr.bad^sub_attr"}}]},
        ),
        ("attr[", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[[]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[]]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[]", {"_errors": [{"code": 108, "context": {"attribute": "attr"}}]}),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr[value eq 1].sub_attr.sub_sub_attr",
            {"_errors": [{"code": 17, "context": {"attribute": "sub_attr.sub_sub_attr"}}]},
        ),
        (
            "attr[value eq 1]sub_attr.sub_sub_attr",
            {
                "_errors": [
                    {"code": 17, "context": {"attribute": "sub_attr.sub_sub_attr"}},
                ]
            },
        ),
        (
            "attr[value eq]",
            {"_errors": [{"code": 103, "context": {"expression": "value eq", "operator": "eq"}}]},
        ),
        (
            "attr[eq 1]",
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "expression": "eq 1",
                            "operator": "1",
                        },
                    }
                ]
            },
        ),
        ("attr[value eq abc]", {"_errors": [{"code": 109, "context": {"value": "abc"}}]}),
        (
            "attr.sub_attr[value eq abc].sub_attr.sub_sub_attr",
            {
                "_errors": [
                    {"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}},
                ]
            },
        ),
    ),
)
def test_patch_path_parsing_failure(path, expected_issues):
    issues = PatchPath.validate(path)
    assert issues.to_dict(context=True) == expected_issues

    with pytest.raises(ValueError, match="invalid path expression"):
        PatchPath.deserialize(path)


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (
            "members",
            PatchPath(
                attr_rep=AttrRep(attr="members"),
                sub_attr_name=None,
                filter_=None,
            ),
        ),
        (
            "name.familyName",
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=AttrName("familyName"),
                filter_=None,
            ),
        ),
        (
            'addresses[type eq "work"]',
            PatchPath(
                attr_rep=AttrRep(attr="addresses"),
                sub_attr_name=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="addresses"),
                        sub_operator=Equal(AttrRep(attr="type"), "work"),
                    )
                ),
            ),
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            PatchPath(
                attr_rep=AttrRep(attr="members"),
                sub_attr_name=AttrName("displayName"),
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="members"),
                        sub_operator=Equal(
                            AttrRep(attr="value"),
                            "2819c223-7f76-453a-919d-413861904646",
                        ),
                    )
                ),
            ),
        ),
    ),
)
def test_patch_path_deserialization_success(path, expected):
    issues = PatchPath.validate(path)
    assert issues.to_dict(message=True) == {}

    deserialized = PatchPath.deserialize(path)
    assert deserialized == expected


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "sub_attr_name": None,
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
        },
        {
            "attr_rep": AttrRep(attr="attr"),
            "sub_attr_name": AttrRep(attr="other_attr"),
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="different_attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
        },
    ),
)
def test_patch_path_object_construction_fails_if_broken_constraints(kwargs):
    with pytest.raises(ValueError):
        PatchPath(**kwargs)


@pytest.mark.parametrize(
    ("path", "expected_filter_value"),
    (
        (
            'emails[value eq "id eq 1 and attr neq 2"]',
            "id eq 1 and attr neq 2",
        ),
        ('emails[value eq "ims[type eq "work"]"]', 'ims[type eq "work"]'),
    ),
)
def test_complex_filter_string_values_can_contain_anything(
    path, expected_filter_value, user_schema
):
    issues = PatchPath.validate(path)
    assert issues.to_dict(message=True) == {}

    deserialized = PatchPath.deserialize(path)
    assert deserialized({"value": expected_filter_value}, user_schema)


@pytest.mark.parametrize(
    ("path", "data", "schema", "expected"),
    (
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            {"type": "work", "value": "my@example.com"},
            "user_schema",
            True,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            42,
            "user_schema",
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            {"type": "home", "value": "my@example.com"},
            "user_schema",
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work'].display"),
            {"type": "work", "value": "my@example.com"},
            "user_schema",
            True,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            "abc",
            "fake_schema",
            True,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            "cba",
            "fake_schema",
            False,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a' or value ew 'a']"),
            "cba",
            "fake_schema",
            True,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            {"bad": "value"},
            "fake_schema",
            False,
        ),
    ),
    indirect=["schema"],
)
def test_check_if_data_matches_path(path, data, schema: ResourceSchema, expected):
    actual = path(data, schema)

    assert actual is expected


def test_trying_to_check_if_data_matches_path_without_filter_fails(user_schema):
    path = PatchPath.deserialize("userName")

    with pytest.raises(AttributeError, match="path has no value selection filter"):
        path(42, user_schema)


def test_patch_path_repr():
    assert (
        repr(PatchPath.deserialize("urn:ietf:params:scim:schemas:core:2.0:User:name.formatted"))
        == "PatchPath(urn:ietf:params:scim:schemas:core:2.0:User:name.formatted)"
    )
    assert (
        repr(PatchPath.deserialize("emails[type eq 'work']")) == "PatchPath(emails[type eq 'work'])"
    )
    assert repr(PatchPath.deserialize("name.formatted")) == "PatchPath(name.formatted)"


@pytest.mark.parametrize(
    ("path_1", "path_2", "expected"),
    (
        (
            PatchPath.deserialize("userName"),
            PatchPath.deserialize("userName"),
            True,
        ),
        (
            PatchPath.deserialize("userName"),
            PatchPath.deserialize("name"),
            False,
        ),
        (
            PatchPath.deserialize("name"),
            PatchPath.deserialize("name.formatted"),
            False,
        ),
        (
            PatchPath.deserialize("name.formatted"),
            PatchPath.deserialize("name.formatted"),
            True,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            PatchPath.deserialize("emails[type eq 'work']"),
            True,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            PatchPath.deserialize("emails[type eq 'home']"),
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            PatchPath.deserialize("emails[type eq 'work'].value"),
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work'].value"),
            PatchPath.deserialize("emails[type eq 'work'].value"),
            True,
        ),
        (
            PatchPath.deserialize("userName"),
            "userName",
            False,
        ),
    ),
)
def test_patch_path_can_be_compared(path_1, path_2, expected):
    assert (path_1 == path_2) is expected


def test_calling_path_for_non_existing_attr_fails(user_schema):
    path = PatchPath.deserialize("non_existing.attr")

    with pytest.raises(ValueError, match="path does not target any attribute"):
        path("whatever", user_schema)


def test_creating_patch_path_with_bad_filter_operator_fails():
    with pytest.raises(ValueError, match="'filter_' must consist of 'ComplexAttributeOperator"):
        PatchPath(
            attr_rep=AttrRep("emails"),
            sub_attr_name=None,
            filter_=Equal(AttrRep("emails"), "user@example.com"),  # noqa
        )


@pytest.mark.parametrize(
    "patch_path",
    (
        "userName",
        "name.formatted",
        "emails[type eq 'work']",
        "emails[type eq 'work'].display",
    ),
)
def test_patch_path_can_be_serialized(patch_path):
    assert PatchPath.deserialize(patch_path).serialize() == patch_path


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_adds_val_for_simple_singular_attr(op_cls, user_schema):
    operations = PatchOperations([op_cls(PatchPath.deserialize("nickName"), "Pagerous")])
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {"nickName": "Pagerous"}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_replaces_existing_val_for_simple_singular_attr(op_cls, user_schema):
    operations = PatchOperations([op_cls(PatchPath.deserialize("nickName"), "Pagerous")])
    data = {"nickname": "NonPagerous"}

    actual = operations.apply(data, user_schema)

    assert actual == {"nickName": "Pagerous"}


def test_add_op_adds_values_for_simple_mv_attr(fake_schema):
    operations = PatchOperations([Add(PatchPath.deserialize("str_mv"), ["b", "c"])])
    data = {}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": ["b", "c"]}


def test_add_op_does_not_filter_duplicates_for_simple_mv_attr(fake_schema):
    operations = PatchOperations([Add(PatchPath.deserialize("str_mv"), ["b", "c"])])
    data = {"str_mv": ["a", "b"]}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": ["a", "b", "b", "c"]}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_adds_val_for_singular_sub_attr_of_complex_attr(op_cls, user_schema):
    operations = PatchOperations(
        [op_cls(PatchPath.deserialize("name"), {"formatted": "John Wick"})]
    )
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": {"formatted": "John Wick"}}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_replaces_existing_val_for_singular_sub_attr_of_complex_attr(op_cls, user_schema):
    operations = PatchOperations([op_cls(PatchPath.deserialize("name.formatted"), "John Wick")])
    data = {"name": {"formatted": "John Doe"}}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": {"formatted": "John Wick"}}


def test_add_op_adds_val_for_mv_sub_attr_of_singular_complex_attr(fake_schema):
    operations = PatchOperations([Add(PatchPath.deserialize("c_str_mv"), {"str": ["c"]})])
    data = {"c_str_mv": {"str": ["a", "b"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["a", "b", "c"]}}


def test_add_op_does_not_filter_duplicate_values_for_mv_sub_attr_of_singular_complex_attr(
    fake_schema,
):
    operations = PatchOperations([Add(PatchPath.deserialize("c_str_mv"), {"str": ["b", "c"]})])
    data = {"c_str_mv": {"str": ["a", "b"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["a", "b", "b", "c"]}}


@pytest.mark.parametrize(
    "op_value",
    ([{"type": "work", "value": "work@mail.com"}], {"type": "work", "value": "work@mail.com"}),
)
def test_add_op_adds_val_for_mv_complex_attribute(user_schema, op_value):
    operations = PatchOperations([Add(PatchPath.deserialize("emails"), op_value)])
    data = {"emails": [{"type": "home", "value": "home@mail.com"}]}

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }


@pytest.mark.parametrize(
    "op_value",
    (
        [{"type": "home", "value": "home@mail.com", "primary": True}],
        {"type": "home", "value": "home@mail.com", "primary": True},
    ),
)
def test_add_op_does_not_merge_complex_items_with_same_sub_attrs(user_schema, op_value):
    operations = PatchOperations([Add(PatchPath.deserialize("emails"), op_value)])
    data = {
        "emails": [
            {"type": "work", "value": "work@mail.com"},
            {"type": "home", "value": "home@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "work", "value": "work@mail.com"},
            {"type": "home", "value": "home@mail.com"},
            {"type": "home", "value": "home@mail.com", "primary": True},
        ]
    }


def test_add_op_adds_sub_attr_values_for_mv_complex_attribute_with_filter(user_schema):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("emails[type eq 'work']"),
                {"display": "Email for work", "primary": True},
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {
                "type": "work",
                "value": "work@mail.com",
                "display": "Email for work",
                "primary": True,
            },
        ]
    }


def test_add_op_fails_if_no_filter_matches_for_mv_complex_attr(user_schema):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("emails[type eq 'work']"),
                {"display": "Email for work", "primary": True},
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
        ]
    }

    with pytest.raises(
        NoTargetException, match="no 'emails' elements matched supplied value selection filter"
    ):
        operations.apply(data, user_schema)


def test_add_op_does_not_filter_duplicates_for_sub_attr_values_of_mv_complex_attribute_with_filter(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("c3_mv[str co 'b']"),
                {"str": ["abc", "ghi"]},
            )
        ]
    )
    data = {
        "c3_mv": [
            {
                "str": ["abc", "jkl"],
                "bool": True,
            },
            {
                "str": ["def"],
                "bool": False,
            },
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {
                "str": ["abc", "jkl", "abc", "ghi"],
                "bool": True,
            },
            {
                "str": ["def"],
                "bool": False,
            },
        ]
    }


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_replaces_values_of_mv_simple_attr_if_filter_matches(
    op_cls,
    fake_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("str_mv[value co 'b']"),
                "<replaced>",
            )
        ]
    )
    data = {"str_mv": ["abc", "def", "ghi", "cba"]}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": ["<replaced>", "def", "ghi", "<replaced>"]}


def test_add_op_fails_if_no_filter_matches_for_mv_simple_attr(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("str_mv[value co 'b']"),
                "<replaced>",
            )
        ]
    )
    data = {"str_mv": ["def", "ghi"]}

    with pytest.raises(
        NoTargetException, match="no 'str_mv' elements matched supplied value selection filter"
    ):
        operations.apply(data, fake_schema)


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_add_op_adds_val_for_singular_sub_attr_of_complex_attr__sub_attr_in_path(
    op_cls,
    user_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("name.formatted"),
                "John Wick",
            )
        ]
    )
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": {"formatted": "John Wick"}}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_add_op_replaces_val_for_singular_sub_attr_of_complex_attr__sub_attr_in_path(
    op_cls,
    user_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("name.formatted"),
                "John Wick",
            )
        ]
    )
    data = {"name": {"formatted": "John Doe"}}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": {"formatted": "John Wick"}}


def test_add_op_adds_val_for_mv_sub_attr_of_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("c_str_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["b", "c"]}}


def test_add_op_does_not_filter_duplicates_for_mv_sub_attr_of_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("c_str_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {"c_str_mv": {"str": ["a", "b"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["a", "b", "b", "c"]}}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_replaces_val_for_existing_singular_sub_attr_of_mv_complex_attr__sub_attr_in_path(
    op_cls,
    user_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("emails.type"),
                "work",
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home"},
            {"type": "private"},
            {"type": "work"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {"emails": [{"type": "work"}, {"type": "work"}, {"type": "work"}]}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_does_not_add_values_for_singular_sub_attr_if_no_mv_complex_attr_items(
    op_cls,
    user_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("emails.type"),
                "work",
            )
        ]
    )
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {}


def test_add_op_adds_val_for_existing_mv_sub_attr_of_mv_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("c3_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {
        "c3_mv": [
            {
                "bool": True,
                "str": ["a"],
            },
            {"bool": False, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "str": ["a", "b", "c"]},
            {"bool": False, "str": ["a", "b", "b", "c"]},
        ]
    }


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_add_op_does_not_add_values_for_mv_sub_attr_if_no_mv_complex_attr_items(
    op_cls,
    fake_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("c3_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {}

    actual = operations.apply(data, fake_schema)

    assert actual == {}


@pytest.mark.parametrize("op_cls", (Add, Replace))
def test_update_op_replaces_val_for_singular_sub_attr_of_filtered_mv_complex_attr__sub_attr_in_path(
    op_cls,
    user_schema,
):
    operations = PatchOperations(
        [
            op_cls(
                PatchPath.deserialize("emails[type eq 'work'].value"),
                "work-2@mail.com",
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
            {"type": "work", "value": "work-2@mail.com"},
        ]
    }


def test_add_op_fails_if_no_filter_matches_for_mv_complex_attr__sub_attr_in_path(
    user_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("emails[type eq 'work'].value"),
                "work-2@mail.com",
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
        ]
    }

    with pytest.raises(
        NoTargetException, match="no 'emails' elements matched supplied value selection filter"
    ):
        operations.apply(data, user_schema)


def test_add_op_adds_val_for_mv_sub_attr_of_filtered_mv_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                PatchPath.deserialize("c3_mv[int gt 10].str"),
                ["b", "c"],
            )
        ]
    )
    data = {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": ["a"]},
            {"bool": True, "int": 12, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": ["a", "b", "c"]},
            {"bool": True, "int": 12, "str": ["a", "b", "b", "c"]},
        ]
    }


def test_add_op_adds_val_for_multiple_attrs_if_no_path_specified(
    fake_schema,
):
    operations = PatchOperations(
        [
            Add(
                None,
                {
                    "int": 42,
                    "str_mv": ["b", "c"],
                    "c": {"value": "<after>"},
                    "c_str_mv": {
                        "str": ["b", "c"],
                    },
                    "c2_mv": [
                        {"str": "<after>", "int": 42},
                        {"str": "<after_2>", "int": 24},
                    ],
                    "c3_mv": [
                        {"str": ["b", "c"], "int": 42},
                        {"str": ["b", "c"], "int": 24},
                    ],
                },
            )
        ]
    )
    data = {
        "str_mv": ["a", "b"],
        "c_str_mv": {"str": ["a", "b"]},
        "c2_mv": [
            {"int": 42},
        ],
        "c3_mv": [{"str": ["a", "b"], "int": 42}, {"int": 24}],
    }
    expected = {
        "int": 42,
        "str_mv": ["a", "b", "b", "c"],
        "c": {"value": "<after>"},
        "c_str_mv": {"str": ["a", "b", "b", "c"]},
        "c2_mv": [
            {"int": 42},
            {"str": "<after>", "int": 42},
            {"str": "<after_2>", "int": 24},
        ],
        "c3_mv": [
            {"str": ["a", "b"], "int": 42},
            {"int": 24},
            {"str": ["b", "c"], "int": 42},
            {"str": ["b", "c"], "int": 24},
        ],
    }

    actual = operations.apply(data, fake_schema)

    assert actual == expected


def test_replace_op_replaces_values_for_simple_mv_attr(fake_schema):
    operations = PatchOperations([Replace(PatchPath.deserialize("str_mv"), ["b", "c"])])
    data = {"str_mv": ["a", "b"]}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": ["b", "c"]}


def test_replace_op_replaces_val_for_mv_sub_attr_of_singular_complex_attr(fake_schema):
    operations = PatchOperations([Replace(PatchPath.deserialize("c_str_mv"), {"str": ["c"]})])
    data = {"c_str_mv": {"str": ["a", "b"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["c"]}}


@pytest.mark.parametrize(
    "op_value",
    ([{"type": "work", "value": "work@mail.com"}], {"type": "work", "value": "work@mail.com"}),
)
def test_replace_op_replaces_val_for_mv_complex_attribute(user_schema, op_value):
    operations = PatchOperations([Replace(PatchPath.deserialize("emails"), op_value)])
    data = {"emails": [{"type": "home", "value": "home@mail.com"}]}

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "work", "value": "work@mail.com"},
        ]
    }


def test_replace_op_replaces_sub_attr_values_for_mv_complex_attribute_with_filter(fake_schema):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("c3_mv[str co 'b']"),
                {"str": ["abc", "ghi"]},
            )
        ]
    )
    data = {
        "c3_mv": [
            {
                "str": ["abc", "jkl"],
                "bool": True,
            },
            {
                "str": ["def"],
                "bool": False,
            },
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {
                "str": ["abc", "ghi"],
                "bool": True,
            },
            {
                "str": ["def"],
                "bool": False,
            },
        ]
    }


def test_replace_op_replaces_val_for_mv_sub_attr_of_complex_attr_if_no_existing__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("c_str_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["b", "c"]}}


def test_replace_op_replaces_val_for_mv_sub_attr_of_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("c_str_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {"c_str_mv": {"str": ["a", "b"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": ["b", "c"]}}


def test_replace_op_replaces_val_for_existing_mv_sub_attr_of_mv_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("c3_mv.str"),
                ["b", "c"],
            )
        ]
    )
    data = {
        "c3_mv": [
            {
                "bool": True,
                "str": ["a"],
            },
            {"bool": False, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "str": ["b", "c"]},
            {"bool": False, "str": ["b", "c"]},
        ]
    }


def test_replace_op_replaces_val_for_mv_sub_attr_of_filtered_mv_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("c3_mv[int gt 10].str"),
                ["b", "c"],
            )
        ]
    )
    data = {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": ["a"]},
            {"bool": True, "int": 12, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": ["b", "c"]},
            {"bool": True, "int": 12, "str": ["b", "c"]},
        ]
    }


def test_replace_op_adds_or_replaces_val_for_multiple_attrs_if_no_path_specified(fake_schema):
    operations = PatchOperations(
        [
            Replace(
                None,
                {
                    "int": 42,
                    "str_mv": ["b", "c"],
                    "c": {"value": "<after>"},
                    "c_str_mv": {
                        "str": ["b", "c"],
                    },
                    "c2_mv": [
                        {"str": "<after>", "int": 42},
                        {"str": "<after_2>", "int": 24},
                    ],
                    "c3_mv": [
                        {"str": ["b", "c"], "int": 42},
                        {"str": ["b", "c"], "int": 24},
                    ],
                },
            )
        ]
    )
    data = {
        "str_mv": ["a", "b"],
        "c_str_mv": {"str": ["a", "b"]},
        "c2_mv": [
            {"int": 42},
        ],
        "c3_mv": [{"str": ["a", "b"], "int": 42}, {"int": 24}],
    }
    expected = {
        "int": 42,
        "str_mv": ["b", "c"],
        "c": {"value": "<after>"},
        "c_str_mv": {"str": ["b", "c"]},
        "c2_mv": [
            {"str": "<after>", "int": 42},
            {"str": "<after_2>", "int": 24},
        ],
        "c3_mv": [
            {"str": ["b", "c"], "int": 42},
            {"str": ["b", "c"], "int": 24},
        ],
    }

    actual = operations.apply(data, fake_schema)

    assert actual == expected


def test_replace_op_fails_if_no_filter_matches_for_mv_complex_attr(user_schema):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("emails[type eq 'work']"),
                {"display": "Email for work", "primary": True},
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
        ]
    }

    with pytest.raises(
        NoTargetException, match="no 'emails' elements matched supplied value selection filter"
    ):
        operations.apply(data, user_schema)


def test_replace_op_fails_if_no_filter_matches_for_mv_simple_attr(fake_schema):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("str_mv[value co 'b']"),
                "<replaced>",
            )
        ]
    )
    data = {"str_mv": ["def", "ghi"]}

    with pytest.raises(
        NoTargetException, match="no 'str_mv' elements matched supplied value selection filter"
    ):
        operations.apply(data, fake_schema)


def test_replace_op_fails_if_no_filter_matches_for_mv_complex_attr__sub_attr_in_path(user_schema):
    operations = PatchOperations(
        [
            Replace(
                PatchPath.deserialize("emails[type eq 'work'].value"),
                "work-2@mail.com",
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
        ]
    }

    with pytest.raises(
        NoTargetException, match="no 'emails' elements matched supplied value selection filter"
    ):
        operations.apply(data, user_schema)


def test_remove_op_removes_val_for_simple_singular_attr(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("nickName"))])
    data = {"nickName": "Pagerous"}

    actual = operations.apply(data, user_schema)

    assert actual == {"nickName": None}


@pytest.mark.parametrize("attr_name", ["nickName", "emails"])
def test_remove_op_passes_if_removing_non_existing_attr(attr_name, user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize(attr_name))])

    actual = operations.apply({}, user_schema)

    assert actual == {}


def test_remove_op_removes_values_for_simple_mv_attr(fake_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("str_mv"))])
    data = {"str_mv": ["b", "c"]}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": []}


def test_remove_op_removes_val_of_complex_attr(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("name"))])
    data = {"name": {"formatted": "John Wick"}}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": None}


def test_remove_op_removes_val_for_mv_complex_attribute(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("emails"))])
    data = {"emails": [{"type": "home", "value": "home@mail.com"}]}

    actual = operations.apply(data, user_schema)

    assert actual == {"emails": []}


def test_remove_op_removes_sub_attr_values_for_mv_complex_attribute_with_filter(user_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("emails[type eq 'work']"),
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
        ]
    }


def test_remove_op_removes_values_of_mv_simple_attr_if_filter_matches(fake_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("str_mv[value co 'b']"),
            )
        ]
    )
    data = {"str_mv": ["abc", "def", "ghi", "cba"]}

    actual = operations.apply(data, fake_schema)

    assert actual == {"str_mv": ["def", "ghi"]}


def test_remove_op_removes_val_for_singular_sub_attr_of_complex_attr__sub_attr_in_path(
    user_schema,
):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("name.formatted"),
            )
        ]
    )
    data = {"name": {"formatted": "John Wick"}}

    actual = operations.apply(data, user_schema)

    assert actual == {"name": {"formatted": None}}


def test_remove_op_does_nothing_if_no_val_complex_attr__sub_attr_in_path(user_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("name.formatted"),
            )
        ]
    )
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {}


def test_remove_op_removes_val_for_mv_sub_attr_of_complex_attr__sub_attr_in_path(fake_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("c_str_mv.str"),
            )
        ]
    )
    data = {"c_str_mv": {"str": ["b", "c"]}}

    actual = operations.apply(data, fake_schema)

    assert actual == {"c_str_mv": {"str": []}}


def test_remove_op_removes_val_for_singular_sub_attr_of_mv_complex_attr__sub_attr_in_path(
    user_schema,
):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("emails.type"),
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": None, "value": "home@mail.com"},
            {"type": None, "value": "private@mail.com"},
            {"type": None, "value": "work@mail.com"},
        ]
    }


def test_remove_op_does_nothing_if_no_val_of_mv_complex_attr__sub_attr_in_path(user_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("emails.type"),
            )
        ]
    )
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {}


def test_remove_op_removes_val_for_mv_sub_attr_of_mv_complex_attr__sub_attr_in_path(fake_schema):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("c3_mv.str"),
            )
        ]
    )
    data = {
        "c3_mv": [
            {
                "bool": True,
                "str": ["a"],
            },
            {"bool": False, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "str": []},
            {"bool": False, "str": []},
        ]
    }


def test_remove_op_removes_val_for_singular_sub_attr_of_filtered_mv_complex_attr__sub_attr_in_path(
    user_schema,
):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("emails[type eq 'work'].value"),
            )
        ]
    )
    data = {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
            {"type": "work", "value": "work@mail.com"},
        ]
    }

    actual = operations.apply(data, user_schema)

    assert actual == {
        "emails": [
            {"type": "home", "value": "home@mail.com"},
            {"type": "private", "value": "private@mail.com"},
            {"type": "work", "value": None},
        ]
    }


def test_remove_op_removes_val_for_mv_sub_attr_of_filtered_mv_complex_attr__sub_attr_in_path(
    fake_schema,
):
    operations = PatchOperations(
        [
            Remove(
                PatchPath.deserialize("c3_mv[int gt 10].str"),
            )
        ]
    )
    data = {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": ["a"]},
            {"bool": True, "int": 12, "str": ["a", "b"]},
        ]
    }

    actual = operations.apply(data, fake_schema)

    assert actual == {
        "c3_mv": [
            {"bool": True, "int": 10, "str": ["a"]},
            {"bool": True, "int": 11, "str": []},
            {"bool": True, "int": 12, "str": []},
        ]
    }


def test_add_op_fails_if_adding_read_only_attribute(user_schema):
    operations = PatchOperations([Add(PatchPath.deserialize("id"), "456")])

    data = {}

    with pytest.raises(
        MutabilityException,
        match=r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:User:id' is read-only",
    ):
        operations.apply(data, user_schema)


def test_replace_op_fails_if_replacing_read_only_attribute(user_schema):
    operations = PatchOperations([Replace(PatchPath.deserialize("id"), "456")])

    data = {"id": "123"}

    with pytest.raises(
        MutabilityException,
        match=r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:User:id' is read-only",
    ):
        operations.apply(data, user_schema)


def test_remove_op_fails_if_removing_read_only_attribute(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("id"))])

    data = {"id": "123"}

    with pytest.raises(
        MutabilityException,
        match=r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:User:id' is read-only",
    ):
        operations.apply(data, user_schema)


def test_add_op_fails_if_replacing_immutable_attribute_that_has_value(group_schema):
    operations = PatchOperations(
        [Add(PatchPath.deserialize("members[value eq '2'].type"), "Group")]
    )

    data = {"members": [{"type": "Group", "value": "1"}, {"type": "User", "value": "2"}]}

    with pytest.raises(
        MutabilityException,
        match=(
            r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:Group:members.type' is immutable"
        ),
    ):
        operations.apply(data, group_schema)


def test_add_op_succeeds_if_adding_immutable_attribute_without_value(group_schema):
    operations = PatchOperations(
        [Add(PatchPath.deserialize("members[value eq '2'].type"), "Group")]
    )
    data = {"members": [{"type": "Group", "value": "1"}, {"value": "2"}]}

    actual = operations.apply(data, group_schema)

    assert actual == {"members": [{"type": "Group", "value": "1"}, {"type": "Group", "value": "2"}]}


def test_replace_op_fails_if_replacing_immutable_attribute_that_has_value(group_schema):
    operations = PatchOperations(
        [Replace(PatchPath.deserialize("members[value eq '2'].type"), "Group")]
    )

    data = {"members": [{"type": "Group", "value": "1"}, {"type": "User", "value": "2"}]}

    with pytest.raises(
        MutabilityException,
        match=(
            r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:Group:members.type' is immutable"
        ),
    ):
        operations.apply(data, group_schema)


def test_replace_op_succeeds_if_adding_immutable_attribute_without_value(group_schema):
    operations = PatchOperations(
        [Replace(PatchPath.deserialize("members[value eq '2'].type"), "Group")]
    )
    data = {"members": [{"type": "Group", "value": "1"}, {"value": "2"}]}

    actual = operations.apply(data, group_schema)

    assert actual == {"members": [{"type": "Group", "value": "1"}, {"type": "Group", "value": "2"}]}


def test_remove_op_fails_if_removing_immutable_attribute_that_has_value(group_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("members[value eq '2'].type"))])

    data = {"members": [{"type": "Group", "value": "1"}, {"type": "User", "value": "2"}]}

    with pytest.raises(
        MutabilityException,
        match=(
            r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:Group:members.type' is immutable"
        ),
    ):
        operations.apply(data, group_schema)


def test_remove_op_fails_if_removing_required_attribute(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("userName"))])
    data = {"userName": "JohnDoe"}

    with pytest.raises(
        MutabilityException,
        match=r"attribute 'urn:ietf:params:scim:schemas:core:2\.0:User:userName' is required",
    ):
        operations.apply(data, user_schema)


def test_remove_op_passes_if_trying_to_remove_required_attribute_which_is_not_present(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("userName"))])
    data = {}

    actual = operations.apply(data, user_schema)

    assert actual == {}


def test_op_fails_if_unknown_attr(user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize("nonExisting"))])

    with pytest.raises(NoTargetException, match="unknown modification target"):
        operations.apply({}, user_schema)


@pytest.mark.parametrize(
    "attr", ["nonExisting", "name.nonExisting", "emails[type eq 'work'].nonExisting"]
)
def test_op_fails_if_unknown_sub_attr(attr, user_schema):
    operations = PatchOperations([Remove(PatchPath.deserialize(attr))])

    with pytest.raises(NoTargetException, match="unknown modification target"):
        operations.apply({}, user_schema)


def test_patch_operation_batches_can_be_compared():
    operations_1 = PatchOperations(
        [
            Add(PatchPath.deserialize("a"), 1),
            Replace(PatchPath.deserialize("b"), "2"),
            Remove(PatchPath.deserialize("c")),
        ]
    )
    operations_2 = PatchOperations(
        [
            Add(PatchPath.deserialize("a"), 1),
            Replace(PatchPath.deserialize("b"), "2"),
            Remove(PatchPath.deserialize("c")),
        ]
    )
    operations_3 = PatchOperations(
        [
            Add(PatchPath.deserialize("a"), 1),
            Replace(PatchPath.deserialize("b"), "2"),
        ]
    )

    assert operations_1 == operations_2
    assert operations_1 != operations_3
    assert operations_1 != "whatever"


def test_patch_operations_can_be_compared():
    operation_1 = Remove(PatchPath.deserialize("a"))
    operation_2 = Remove(PatchPath.deserialize("a"))
    operation_3 = Remove(PatchPath.deserialize("b"))

    assert operation_1 == operation_2
    assert operation_1 != operation_3
    assert operation_1 != "whatever"
