import pytest
from _pytest.outcomes import Failed
from scimpler.testing import assert_response
from scimpler.validator import ResourceObjectGet
from scimpler.warning import ScimplerCompatibilityWarning


def test_warning_is_raised_if_validation_warning(user_schema):
    validator = ResourceObjectGet(resource_schema=user_schema)

    with pytest.warns(ScimplerCompatibilityWarning, match="not a valid phone number"):
        assert_response(
            validator,
            status_code=200,
            body={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": "1",
                "userName": "johndoe",
                "phoneNumbers": [{"value": "you've picked wrong number!"}],
                "meta": {"version": "1"},
            },
            headers={"ETag": "1"},
        )


def test_cause_test_failure_if_validation_error(user_schema):
    validator = ResourceObjectGet(resource_schema=user_schema)

    with pytest.raises(Failed, match="missing"):
        assert_response(
            validator,
            status_code=200,
            body={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": "1",
                "meta": {"version": "1"},
            },
            headers={"ETag": "1"},
        )
