from src.assets.scim_error import create_error


def test_scim_error_can_be_created():
    expected = {
        "status": "400",
        "scimType": "invalidFilter",
        "detail": "bad filter",
    }

    actual = create_error(status=400, scim_type="invalidFilter", detail="bad filter")

    assert actual == expected
