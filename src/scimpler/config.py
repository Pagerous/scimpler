from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class _GenericOption:
    supported: bool = False


@dataclass
class _BulkOption(_GenericOption):
    max_operations: Optional[int] = None
    max_payload_size: Optional[int] = None
    supported: bool = False

    def __post_init__(self):
        if self.supported and not all([self.max_payload_size, self.max_operations]):
            raise ValueError(
                "'max_payload_size' and 'max_operations' must be specified "
                "if bulk operations are supported"
            )


@dataclass
class _FilterOption(_GenericOption):
    max_results: Optional[int] = None
    supported: bool = False

    def __post_init__(self):
        if self.supported and not self.max_results:
            raise ValueError("'max_results' must be specified if filtering is supported")


@dataclass
class _AuthenticationScheme:
    name: str
    description: str
    spec_uri: str
    documentation_uri: str
    type: str


@dataclass
class ServiceProviderConfig:
    documentation_uri: str
    patch: _GenericOption
    bulk: _BulkOption
    filter: _FilterOption
    change_password: _GenericOption
    sort: _GenericOption
    etag: _GenericOption
    authentication_schemes: list[_AuthenticationScheme]


def create_service_provider_config(
    documentation_uri: str = "",
    patch: Optional[dict[str, Any]] = None,
    bulk: Optional[dict[str, Any]] = None,
    filter_: Optional[dict[str, Any]] = None,
    change_password: Optional[dict[str, Any]] = None,
    sort: Optional[dict[str, Any]] = None,
    etag: Optional[dict[str, Any]] = None,
    authentication_schemes: Optional[list[dict[str, Any]]] = None,
):
    return ServiceProviderConfig(
        documentation_uri=documentation_uri,
        patch=_GenericOption(**(patch or {})),
        bulk=_BulkOption(**(bulk or {})),
        filter=_FilterOption(**(filter_ or {})),
        change_password=_GenericOption(**(change_password or {})),
        sort=_GenericOption(**(sort or {})),
        etag=_GenericOption(**(etag or {})),
        authentication_schemes=[
            _AuthenticationScheme(**item) for item in authentication_schemes or []
        ],
    )


service_provider_config: ServiceProviderConfig = create_service_provider_config()


def set_service_provider_config(config: ServiceProviderConfig):
    global service_provider_config
    service_provider_config = config
