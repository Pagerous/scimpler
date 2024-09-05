import pytest

from scimpler.data.identifiers import AttrRep, BoundedAttrRep


def test_bounded_attr_creation_fails_if_bad_attr_name():
    with pytest.raises(ValueError, match="is not valid attr name"):
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="bad^attr",
        )


def test_bounded_attr_creation_fails_if_bad_sub_attr_name():
    with pytest.raises(ValueError, match="'.*' is not valid attr name"):
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attr="attr",
            sub_attr="bad^sub^attr",
        )


@pytest.mark.parametrize(
    ("attr_1", "attr_2", "expected"),
    (
        (AttrRep(attr="attr"), AttrRep(attr="ATTR"), True),
        (AttrRep(attr="abc"), AttrRep(attr="cba"), False),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="userName"),
            AttrRep(attr="UserName"),
            True,
        ),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="name"),
            BoundedAttrRep(schema="urn:ietf:params:SCIM:schemas:core:2.0:user", attr="NAME"),
            True,
        ),
        (
            BoundedAttrRep(schema="urn:ietf:params:scim:schemas:core:2.0:User", attr="nonExisting"),
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="nonExisting",
            ),
            False,
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="formatted",
            ),
            BoundedAttrRep(
                schema="urn:ietf:params:SCIM:schemas:core:2.0:User",
                attr="NAME",
                sub_attr="FORMATTED",
            ),
            True,
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="givenName",
            ),
            BoundedAttrRep(
                schema="urn:ietf:params:SCIM:schemas:core:2.0:User",
                attr="NAME",
                sub_attr="FORMATTED",
            ),
            False,
        ),
        (AttrRep(attr="attr"), "attr", False),
    ),
)
def test_attr_rep_can_be_compared(attr_1, attr_2, expected):
    assert (attr_1 == attr_2) is expected
