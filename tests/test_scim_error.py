from scimpler.error import create_error


def test_full_scim_error_can_be_created():
    expected = {
        "status": "400",
        "scimType": "invalidFilter",
        "detail": "bad filter",
    }

    actual = create_error(status=400, scim_type="invalidFilter", detail="bad filter")

    assert actual == expected


def test_scim_error_with_status_only():
    expected = {"status": "403"}

    actual = create_error(status=403)

    assert actual == expected
