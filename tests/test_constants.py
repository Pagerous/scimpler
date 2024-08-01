from scimpler.constants import SCIMType


def test_scim_type_repr():
    assert repr(SCIMType("integer")) == "SCIMType(integer)"
