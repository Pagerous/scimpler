import pytest

from scimpler.config import ServiceProviderConfig


def test_value_error_is_raised_if_options_not_specified_for_bulk_operation():
    with pytest.raises(
        ValueError,
        match=(
            "'max_payload_size' and 'max_operations' must be specified "
            "if bulk operations are supported"
        ),
    ):
        ServiceProviderConfig.create(bulk={"supported": True})


def test_value_error_is_raised_if_options_not_specified_for_filter_operation():
    with pytest.raises(
        ValueError,
        match="'max_results' must be specified if filtering is supported",
    ):
        ServiceProviderConfig.create(filter_={"supported": True})
