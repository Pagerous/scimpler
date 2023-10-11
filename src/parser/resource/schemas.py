import abc
from typing import Dict, List

from src.parser.attributes import common as common_attrs
from src.parser.attributes import error as error_attrs
from src.parser.attributes import list_result as query_result_attrs
from src.parser.attributes import user as user_attrs
from src.parser.attributes.attributes import Attribute


class Schema(abc.ABC):
    @property
    @abc.abstractmethod
    def attributes(self) -> Dict[str, Attribute]: ...

    @property
    @abc.abstractmethod
    def schemas(self) -> List[str]:
        ...

    @abc.abstractmethod
    def __repr__(self):
        ...


class ErrorSchema(Schema):
    def __init__(self):
        self._attributes = {
            common_attrs.schemas.name: common_attrs.schemas,
            error_attrs.status.name: error_attrs.status,
            error_attrs.scim_type.name: error_attrs.scim_type,
            error_attrs.detail.name: error_attrs.detail,
        }

    def __repr__(self) -> str:
        return "Error"

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return self._attributes

    @property
    def schemas(self) -> List[str]:
        return ["urn:ietf:params:scim:api:messages:2.0:Error"]


class ListResponseSchema(Schema):
    def __init__(self):
        self._attributes = {  # 'Resources' are special and not included here
            common_attrs.schemas.name: common_attrs.schemas,
            query_result_attrs.total_results.name: query_result_attrs.total_results,
            query_result_attrs.start_index.name: query_result_attrs.start_index,
            query_result_attrs.items_per_page.name: query_result_attrs.items_per_page,
        }

    def __repr__(self) -> str:
        return "ListResponse"

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return self._attributes

    @property
    def schemas(self) -> List[str]:
        return ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]


class ResourceSchema(Schema, abc.ABC):
    def __init__(self, *core_attributes: Attribute):
        self._attributes = {
            common_attrs.schemas.name: common_attrs.schemas,
            common_attrs.id_.name: common_attrs.id_,
            common_attrs.external_id.name: common_attrs.external_id,
            common_attrs.meta.name: common_attrs.meta,
            **{attr.name: attr for attr in core_attributes},
        }

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return self._attributes


class UserSchema(ResourceSchema):
    def __init__(self):
        super().__init__(
            user_attrs.user_name,
            user_attrs.name,
            user_attrs.display_name,
            user_attrs.nick_name,
            user_attrs.profile_url,
            user_attrs.title,
            user_attrs.user_type,
            user_attrs.preferred_language,
            user_attrs.locale,
            user_attrs.timezone,
            user_attrs.active,
            user_attrs.password,
            user_attrs.emails,
            user_attrs.ims,
            user_attrs.photos,
            user_attrs.addresses,
            user_attrs.groups,
            user_attrs.entitlements,
            user_attrs.roles,
            user_attrs.x509_certificates,
        )

    @property
    def schemas(self) -> List[str]:
        return ["urn:ietf:params:scim:schemas:core:2.0:User"]

    def __repr__(self) -> str:
        return "User"
