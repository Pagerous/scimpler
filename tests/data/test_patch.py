import pytest

from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep
from scimpler.data.operator import ComplexAttributeOperator, Equal
from scimpler.data.patch import PatchPath
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
