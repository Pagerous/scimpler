from copy import deepcopy

import marshmallow

from src.assets.config import create_service_provider_config
from src.assets.schemas import User, Group
from src.data.attrs import DateTime
from src.ext.marshmallow import initialize, response_serializer
from src.request.validator import ResourceObjectGET, ServerRootResourcesGET

CONFIG = create_service_provider_config(
    patch={"supported": True},
    bulk={"max_operations": 10, "max_payload_size": 4242, "supported": True},
    filter_={"max_results": 100, "supported": True},
    change_password={"supported": True},
    sort={"supported": True},
    etag={"supported": True},
)


def test_response_serializer_can_be_created():
    initialize({DateTime: marshmallow.fields.String})

    validator = ResourceObjectGET(config=CONFIG, resource_schema=User)
    schema_cls = response_serializer(validator)

    schema_cls().dump({"id": 123})


def test_list_response_can_be_serialized(list_data):
    initialize({DateTime: marshmallow.fields.String})

    validator = ServerRootResourcesGET(config=CONFIG, resource_schemas=[User, Group])
    schema_cls = response_serializer(validator)

    dumped = schema_cls().dump(deepcopy(list_data))

    assert dumped == list_data
