from src.assets.config import create_service_provider_config
from src.assets.schemas import user
from src.ext.marshmallow import response_serializer
from src.request_validator import ResourceObjectGET, ServerRootResourcesGET

CONFIG = create_service_provider_config(
    patch={"supported": True},
    bulk={"max_operations": 10, "max_payload_size": 4242, "supported": True},
    filter_={"max_results": 100, "supported": True},
    change_password={"supported": True},
    sort={"supported": True},
    etag={"supported": True},
)


def test_response_serializer_can_be_created():
    validator = ResourceObjectGET(config=CONFIG, resource_schema=user.User)
    schema_cls = response_serializer(validator)

    schema_cls().dump({"id": 123})


def test_list_response_serializer_can_be_created():
    validator = ServerRootResourcesGET(config=CONFIG, resource_schemas=[user.User])
    schema_cls = response_serializer(validator)
