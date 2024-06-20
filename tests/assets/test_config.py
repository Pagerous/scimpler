import pytest

from src.config import create_service_provider_config


def test_value_error_is_raised_if_options_not_specified_for_bulk_operation():
    with pytest.raises(
        ValueError,
        match=(
            "'max_payload_size' and 'max_operations' must be specified "
            "if bulk operations are supported"
        ),
    ):
        create_service_provider_config(bulk={"supported": True})


def test_value_error_is_raised_if_options_not_specified_for_filter_operation():
    with pytest.raises(
        ValueError,
        match="'max_results' must be specified if filtering is supported",
    ):
        create_service_provider_config(filter_={"supported": True})
