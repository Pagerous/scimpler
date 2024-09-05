import pytest

from scimpler.data.attr_presence import (
    AttrPresenceConfig,
    DataInclusivity,
    validate_presence,
)
from scimpler.identifiers import AttrRep


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

    assert issues.to_dict(msg=True) == {}


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

    assert issues.to_dict(msg=True) == {}


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
        AttrPresenceConfig(direction="RESPONSE", attr_reps=[AttrRep(attr="attr")])
