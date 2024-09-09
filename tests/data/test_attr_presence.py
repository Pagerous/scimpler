import pytest

from scimpler.data import BoundedAttrRep
from scimpler.data.attr_value_presence import (
    AttrValuePresenceConfig,
    DataInclusivity,
    validate_presence,
)
from scimpler.data.identifiers import AttrRep


def test_presence_validation_fails_if_returned_attribute_that_never_should_be_returned(user_schema):
    expected = {
        "_errors": [
            {
                "code": 7,
            }
        ]
    }

    issues = validate_presence(
        attr=user_schema.attrs.get("password"),
        value="1234",
        direction="RESPONSE",
    )

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(user_schema):
    issues = validate_presence(
        attr=user_schema.attrs.get("password"),
        value="1234",
        direction="REQUEST",
    )

    assert issues.to_dict(message=True) == {}


def test_presence_validation_fails_on_attr_which_should_not_be_included_if_not_necessary(
    user_schema,
):
    expected = {"_errors": [{"code": 7}]}

    issues = validate_presence(
        attr=user_schema.attrs.get("name"),
        value={"givenName": "Arkadiusz", "familyName": "Pajor"},
        direction="RESPONSE",
        inclusivity=DataInclusivity.EXCLUDE,
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_if_not_provided_attribute_that_always_should_be_returned(
    user_schema,
):
    expected = {
        "_errors": [
            {
                "code": 5,
            }
        ]
    }

    issues = validate_presence(
        attr=user_schema.attrs.get("id"),
        value=None,
        direction="RESPONSE",
    )

    assert issues.to_dict() == expected


def test_presence_validation_passes_if_not_provided_requested_optional_attribute(user_schema):
    issues = validate_presence(
        attr=user_schema.attrs.get("name.familyName"),
        value=None,
        direction="RESPONSE",
        inclusivity=DataInclusivity.INCLUDE,
    )

    assert issues.to_dict(message=True) == {}


def test_specifying_attribute_issued_by_service_provider_causes_validation_failure(user_schema):
    expected_issues = {"_errors": [{"code": 6}]}

    issues = validate_presence(
        attr=user_schema.attrs.get("id"),
        value="should-not-be-provided",
        direction="REQUEST",
    )

    assert issues.to_dict() == expected_issues


def test_creating_presence_config_with_attr_reps_and_no_inclusiveness_specified_fails():
    with pytest.raises(ValueError, match="'include' must be specified if 'attr_reps' is specified"):
        AttrValuePresenceConfig(direction="RESPONSE", attr_reps=[AttrRep(attr="attr")])


@pytest.mark.parametrize(
    ("attr_rep", "presence_config", "expected"),
    (
        (
            AttrRep(attr="userName"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=True
            ),
            True,
        ),
        (
            AttrRep(attr="userName"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            False,
        ),
        (
            AttrRep(attr="name", sub_attr="formatted"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            True,
        ),
        (
            AttrRep(attr="name"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="formatted")],
                include=True,
            ),
            True,
        ),
        (
            AttrRep(attr="userName"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=False
            ),
            False,
        ),
        (
            AttrRep(attr="userName"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            True,
        ),
        (
            AttrRep(attr="name", sub_attr="formatted"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            False,
        ),
        (
            AttrRep(attr="name"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="formatted")],
                include=False,
            ),
            True,
        ),
        (
            AttrRep(attr="emails"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="type")],
                include=False,
            ),
            True,
        ),
        (
            AttrRep(attr="emails"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="value")],
                include=False,
            ),
            True,
        ),
        (
            AttrRep(attr="emails"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="value")],
                include=True,
            ),
            True,
        ),
        (
            AttrRep(attr="emails"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[
                    AttrRep(attr="emails", sub_attr="value"),
                    AttrRep(attr="emails", sub_attr="primary"),
                ],
                include=True,
            ),
            True,
        ),
        (
            AttrRep(attr="emails", sub_attr="value"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[
                    AttrRep(attr="emails", sub_attr="type"),
                ],
                include=False,
            ),
            True,
        ),
        (
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="meta",
                sub_attr="location",
            ),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[
                    BoundedAttrRep(
                        schema="urn:ietf:params:scim:schemas:core:2.0:Group",
                        attr="meta",
                        sub_attr="location",
                    ),
                ],
                include=False,
            ),
            True,
        ),
    ),
)
def test_allowed(attr_rep, presence_config, expected):
    assert presence_config.allowed(attr_rep) == expected
