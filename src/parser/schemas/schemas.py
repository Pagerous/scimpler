import abc
from typing import Any, Dict, List

from src.parser.attributes import common as common_attrs
from src.parser.attributes import error as error_attrs
from src.parser.attributes import user as user_attrs
from src.parser.attributes.attributes import Attribute
from src.parser.error import ValidationError


class Schema(abc.ABC):
    @property
    @abc.abstractmethod
    def attributes(self) -> Dict[str, Attribute]: ...

    def validate_request(self, http_method: str, body: Dict[str, Any]) -> List[ValidationError]:
        validation_errors = []
        if http_method in ["POST"]:
            for attr_name, attr in self.attributes.items():
                validation_errors.extend(
                    [
                        error.with_location("body", "request")
                        for error in attr.validate(body.get(attr_name), http_method, "REQUEST")
                    ]
                )
        return validation_errors

    def validate_response(
        self,
        http_method: str,
        request_body: Dict[str, Any],
        response_body: Dict[str, Any]
    ) -> List[ValidationError]:
        validation_errors = []
        if http_method in ["POST"]:
            for attr_name, attr in self.attributes.items():
                validation_errors.extend(
                    [
                        error.with_location("body", "response")
                        for error in attr.validate(response_body.get(attr_name), http_method, "RESPONSE")
                    ]
                )
        return validation_errors


class ErrorSchema(Schema):
    def __init__(self):
        self.schemas_attribute = common_attrs.schemas
        self.core_attributes = {
            error_attrs.status.name.lower(): error_attrs.status,
            error_attrs.scim_type.name.lower(): error_attrs.scim_type,
            error_attrs.detail.name.lower(): error_attrs.detail,
        }

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return {
            "schemas": self.schemas_attribute,
            **self.core_attributes
        }

    def validate_request(self, http_method: str, body: Dict[str, Any]) -> List[ValidationError]:
        return []


class ResourceSchema(Schema):
    def __init__(self, *core_attributes: Attribute, resource_type: str):
        self._resource_type = resource_type
        self.schemas_attribute = common_attrs.schemas
        self.common_attributes = {
            common_attrs.id_.name.lower(): common_attrs.id_,
            common_attrs.external_id.name.lower(): common_attrs.external_id,
            common_attrs.meta.name.lower(): common_attrs.meta
        }
        self.core_attributes = {attr.name.lower(): attr for attr in core_attributes}

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return {
            "schemas": self.schemas_attribute,
            **self.common_attributes,
            **self.core_attributes
        }

    def validate_response(
        self,
        http_method: str,
        request_body: Dict[str, Any],
        response_body: Dict[str, Any]
    ) -> List[ValidationError]:
        validation_errors = super().validate_response(http_method, request_body, response_body)
        meta = response_body.get("meta", {})
        if isinstance(meta, dict):
            resource_type = meta.get("resourceType")
            if resource_type is not None and resource_type != self._resource_type:
                validation_errors.append(
                    ValidationError.resource_type_mismatch(
                        resource_type=self._resource_type, provided=resource_type)
                    .with_location("resourceType", "meta", "body", "response")
                )
        return validation_errors


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
            resource_type="User",
        )
