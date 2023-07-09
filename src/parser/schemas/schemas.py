import abc
from typing import Any, Dict, List, Optional

from src.parser.attributes import common as common_attrs
from src.parser.attributes import error as error_attrs
from src.parser.attributes import query_result as query_result_attrs
from src.parser.attributes import user as user_attrs
from src.parser.attributes.attributes import Attribute
from src.parser.error import ValidationError


class Schema(abc.ABC):
    @property
    @abc.abstractmethod
    def attributes(self) -> Dict[str, Attribute]: ...

    def validate_request(
        self,
        http_method: str,
        body: Dict[str, Any],
        headers: Dict[str, Any],
        query_string: Dict[str, Any],
    ) -> List[ValidationError]:
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
        status_code: int,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        response_body: Dict[str, Any],
        response_headers: Dict[str, Any],
    ) -> List[ValidationError]:
        validation_errors = []
        if http_method in ["POST", "GET"]:
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

    def validate_response(
        self,
        http_method: str,
        status_code: int,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        response_body: Dict[str, Any],
        response_headers: Dict[str, Any],
    ) -> List[ValidationError]:
        validation_errors = super().validate_response(
            http_method=http_method,
            status_code=status_code,
            request_body=request_body,
            request_headers=request_headers,
            request_query_string=request_query_string,
            response_body=response_body,
            response_headers=response_headers,
        )
        if str(status_code) != response_body.get("status"):
            validation_errors.append(
                ValidationError.error_status_mismatch(
                    str(status_code), response_body.get("status")
                ).with_location("status", "body", "response")
            )
            validation_errors.append(
                ValidationError.error_status_mismatch(
                    str(status_code), response_body.get("status")
                ).with_location("status", "response")
            )
        if not 200 <= status_code < 600:
            validation_errors.append(
                ValidationError.bad_error_status(status_code).with_location("status", "response")
            )
        return validation_errors

    def validate_request(
        self,
        http_method: str,
        body: Dict[str, Any],
        headers: Dict[str, Any],
        query_string: Dict[str, Any],
    ) -> List[ValidationError]:
        return []


class ListResponseSchema(Schema):
    def __init__(self):
        self.schemas_attribute = common_attrs.schemas
        self.core_attributes = {  # 'Resources' are special and not included here
            query_result_attrs.total_results.name.lower(): query_result_attrs.total_results,
            query_result_attrs.start_index.name.lower(): query_result_attrs.start_index,
            query_result_attrs.items_per_page.name.lower(): query_result_attrs.items_per_page,
        }
        self._resource_schema: Optional[Schema] = None

    def set_resource_schema(self, schema: Schema) -> None:
        self._resource_schema = schema

    @property
    def attributes(self) -> Dict[str, Attribute]:
        return {
            "schemas": self.schemas_attribute,
            **self.core_attributes
        }

    def validate_response(
        self,
        http_method: str,
        status_code: int,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        response_body: Dict[str, Any],
        response_headers: Dict[str, Any],
    ) -> List[ValidationError]:
        if http_method != "GET":
            return []
        validation_errors = super().validate_response(
            http_method=http_method,
            status_code=status_code,
            request_body=request_body,
            request_headers=request_headers,
            request_query_string=request_query_string,
            response_body=response_body,
            response_headers=response_headers,
        )
        if validation_errors:
            return validation_errors
        if self._resource_schema is None:
            for i, resource in enumerate(response_body.get("resources", [])):
                if "id" not in resource:
                    validation_errors.append(
                        ValidationError.missing_required_attribute(
                            "id"
                        ).with_location("id", i, "Resources", "body", "response")
                    )
        else:
            for i, resource in enumerate(response_body.get("resources", [])):
                for attr_name, attr in self._resource_schema.attributes.items():
                    if attr_name == "schemas":
                        continue  # "schemas" is not required for response list item
                    validation_errors.extend(
                        [
                            error.with_location(i, "Resources", "body", "response")
                            for error in attr.validate(resource.get(attr_name), http_method, "RESPONSE")
                        ]
                    )
                    # TODO: validate according to "attributes" query param too
        # TODO: validate remaining list parameters when pagination

        if status_code != 200:
            validation_errors.append(
                ValidationError.bad_status_code("GET", 200, status_code).with_location("status", "response")
            )

        return validation_errors


class ResourceSchema(Schema, abc.ABC):
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
        status_code: int,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        response_body: Dict[str, Any],
        response_headers: Dict[str, Any],
    ) -> List[ValidationError]:
        validation_errors = super().validate_response(
            http_method=http_method,
            status_code=status_code,
            request_body=response_body,
            request_headers=request_headers,
            request_query_string=request_query_string,
            response_body=response_body,
            response_headers=response_headers,
        )
        meta = response_body.get("meta", {})
        if isinstance(meta, dict):
            resource_type = meta.get("resourcetype")
            if resource_type is not None and resource_type != self._resource_type:
                validation_errors.append(
                    ValidationError.resource_type_mismatch(
                        resource_type=self._resource_type, provided=resource_type)
                    .with_location("resourceType", "meta", "body", "response")
                )
        if http_method == "POST":
            validation_errors.extend(
                self._validate_location_header(
                    response_body=response_body,
                    response_headers=response_headers,
                    header_optional=False,
                )
            )
            if status_code != 201:
                validation_errors.append(
                    ValidationError.bad_status_code("POST", 201, status_code).with_location("status", "response")
                )
        elif http_method in ["GET"]:
            validation_errors.extend(
                self._validate_location_header(
                    response_body=response_body,
                    response_headers=response_headers,
                    header_optional=True,
                )
            )
            if status_code != 200:
                validation_errors.append(
                    ValidationError.bad_status_code("GET", 200, status_code).with_location("status", "response")
                )
        return validation_errors

    @staticmethod
    def _validate_location_header(
        response_body: Dict[str, Any],
        response_headers: Optional[Dict[str, Any]],
        header_optional: bool
    ) -> List[ValidationError]:
        validation_errors = []
        meta = response_body.get("meta")
        if isinstance(meta, dict):
            meta_location = meta.get("location")
        else:
            meta_location = None
        if "Location" not in (response_headers or {}):
            if not header_optional:
                validation_errors.append(
                    ValidationError.missing_required_header("Location").with_location("headers", "response")
                )
            else:
                return validation_errors
        elif meta_location != response_headers["Location"]:
            validation_errors.append(
                ValidationError.values_must_match(
                    value_1="'Location' header", value_2="'meta.location' attribute"
                ).with_location("location", "meta", "body", "response")
            )
            validation_errors.append(
                ValidationError.values_must_match(
                    value_1="'Location' header", value_2="'meta.location' attribute"
                ).with_location("headers", "response")
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
