"""Comprehensive tests for pbx/api/openapi.py OpenAPI specification."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.api.openapi import get_openapi_spec


@pytest.mark.unit
class TestOpenAPISpecTopLevel:
    """Tests for the top-level structure of the OpenAPI specification."""

    def test_returns_dict(self) -> None:
        """get_openapi_spec must return a dictionary."""
        spec = get_openapi_spec()
        assert isinstance(spec, dict)

    def test_openapi_version(self) -> None:
        """Spec must declare OpenAPI 3.0.3."""
        spec = get_openapi_spec()
        assert spec["openapi"] == "3.0.3"

    def test_top_level_keys_present(self) -> None:
        """All required top-level keys must be present."""
        spec = get_openapi_spec()
        required_keys = {"openapi", "info", "servers", "tags", "paths", "components"}
        assert required_keys.issubset(spec.keys())

    def test_spec_is_new_instance_each_call(self) -> None:
        """Each call should return a separate dict (not a shared mutable reference)."""
        spec_a = get_openapi_spec()
        spec_b = get_openapi_spec()
        assert spec_a == spec_b
        assert spec_a is not spec_b


@pytest.mark.unit
class TestOpenAPIInfo:
    """Tests for the info section of the OpenAPI specification."""

    def test_info_title(self) -> None:
        """Info title must be 'PBX API'."""
        info = get_openapi_spec()["info"]
        assert info["title"] == "PBX API"

    def test_info_version(self) -> None:
        """Info version must be '1.0.0'."""
        info = get_openapi_spec()["info"]
        assert info["version"] == "1.0.0"

    def test_info_description_present(self) -> None:
        """Info description must be a non-empty string."""
        info = get_openapi_spec()["info"]
        assert isinstance(info["description"], str)
        assert len(info["description"]) > 0

    def test_info_contact(self) -> None:
        """Info contact section must include a name."""
        info = get_openapi_spec()["info"]
        assert "contact" in info
        assert info["contact"]["name"] == "PBX Admin"

    def test_info_license(self) -> None:
        """Info license section must declare Proprietary."""
        info = get_openapi_spec()["info"]
        assert "license" in info
        assert info["license"]["name"] == "Proprietary"


@pytest.mark.unit
class TestOpenAPIServers:
    """Tests for the servers section."""

    def test_servers_list_not_empty(self) -> None:
        """Servers list must contain at least one entry."""
        servers = get_openapi_spec()["servers"]
        assert isinstance(servers, list)
        assert len(servers) >= 1

    def test_current_server_url(self) -> None:
        """Default server URL must be '/'."""
        servers = get_openapi_spec()["servers"]
        assert servers[0]["url"] == "/"

    def test_current_server_description(self) -> None:
        """Default server must have description 'Current server'."""
        servers = get_openapi_spec()["servers"]
        assert servers[0]["description"] == "Current server"


@pytest.mark.unit
class TestOpenAPITags:
    """Tests for the tags section."""

    def test_tag_count(self) -> None:
        """There must be exactly 5 tags."""
        tags = get_openapi_spec()["tags"]
        assert len(tags) == 5

    def test_tag_names(self) -> None:
        """Tags must include Health, Auth, Extensions, Calls, Config."""
        tags = get_openapi_spec()["tags"]
        tag_names = {t["name"] for t in tags}
        expected = {"Health", "Auth", "Extensions", "Calls", "Config"}
        assert tag_names == expected

    def test_all_tags_have_descriptions(self) -> None:
        """Every tag must have a non-empty description."""
        tags = get_openapi_spec()["tags"]
        for tag in tags:
            assert "description" in tag
            assert isinstance(tag["description"], str)
            assert len(tag["description"]) > 0


@pytest.mark.unit
class TestOpenAPIPaths:
    """Tests for the paths section -- endpoint presence and structure."""

    def test_all_expected_paths_present(self) -> None:
        """All documented paths must exist."""
        paths = get_openapi_spec()["paths"]
        expected_paths = [
            "/health",
            "/api/health/detailed",
            "/api/status",
            "/api/auth/login",
            "/api/auth/logout",
            "/api/extensions",
            "/api/extensions/{number}",
            "/api/calls",
            "/api/statistics",
            "/api/config",
            "/api/config/full",
        ]
        for path in expected_paths:
            assert path in paths, f"Missing path: {path}"

    def test_total_path_count(self) -> None:
        """Verify the total number of paths."""
        paths = get_openapi_spec()["paths"]
        assert len(paths) == 11


@pytest.mark.unit
class TestHealthEndpoints:
    """Tests for /health, /api/health/detailed, and /api/status paths."""

    def test_health_check_is_get(self) -> None:
        """GET /health must be defined."""
        path = get_openapi_spec()["paths"]["/health"]
        assert "get" in path

    def test_health_check_operation_id(self) -> None:
        """GET /health operationId must be 'healthCheck'."""
        op = get_openapi_spec()["paths"]["/health"]["get"]
        assert op["operationId"] == "healthCheck"

    def test_health_check_tags(self) -> None:
        """GET /health must be tagged 'Health'."""
        op = get_openapi_spec()["paths"]["/health"]["get"]
        assert "Health" in op["tags"]

    def test_health_check_responses(self) -> None:
        """GET /health must define 200 and 503 responses."""
        responses = get_openapi_spec()["paths"]["/health"]["get"]["responses"]
        assert "200" in responses
        assert "503" in responses

    def test_health_check_200_schema_ref(self) -> None:
        """200 response must reference HealthResponse schema."""
        schema = (
            get_openapi_spec()["paths"]["/health"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/HealthResponse"

    def test_detailed_health_operation_id(self) -> None:
        """GET /api/health/detailed operationId must be 'detailedHealth'."""
        op = get_openapi_spec()["paths"]["/api/health/detailed"]["get"]
        assert op["operationId"] == "detailedHealth"

    def test_detailed_health_overall_status_enum(self) -> None:
        """Detailed health must define overall_status enum."""
        schema = (
            get_openapi_spec()["paths"]["/api/health/detailed"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        overall = schema["properties"]["overall_status"]
        assert overall["enum"] == ["healthy", "degraded", "unhealthy"]

    def test_detailed_health_components_property(self) -> None:
        """Detailed health must include a components property."""
        schema = (
            get_openapi_spec()["paths"]["/api/health/detailed"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert "components" in schema["properties"]

    def test_status_endpoint_operation_id(self) -> None:
        """GET /api/status operationId must be 'getStatus'."""
        op = get_openapi_spec()["paths"]["/api/status"]["get"]
        assert op["operationId"] == "getStatus"

    def test_status_endpoint_responses(self) -> None:
        """GET /api/status must define 200 and 500 responses."""
        responses = get_openapi_spec()["paths"]["/api/status"]["get"]["responses"]
        assert "200" in responses
        assert "500" in responses

    def test_status_endpoint_500_error_ref(self) -> None:
        """500 response must reference Error schema."""
        schema = (
            get_openapi_spec()["paths"]["/api/status"]["get"]["responses"]["500"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/Error"


@pytest.mark.unit
class TestAuthEndpoints:
    """Tests for /api/auth/login and /api/auth/logout paths."""

    def test_login_is_post(self) -> None:
        """POST /api/auth/login must be defined."""
        path = get_openapi_spec()["paths"]["/api/auth/login"]
        assert "post" in path

    def test_login_operation_id(self) -> None:
        """Login operationId must be 'login'."""
        op = get_openapi_spec()["paths"]["/api/auth/login"]["post"]
        assert op["operationId"] == "login"

    def test_login_request_body_required(self) -> None:
        """Login must require a request body."""
        op = get_openapi_spec()["paths"]["/api/auth/login"]["post"]
        assert op["requestBody"]["required"] is True

    def test_login_request_body_schema_ref(self) -> None:
        """Login request body must reference LoginRequest."""
        schema = (
            get_openapi_spec()["paths"]["/api/auth/login"]["post"]["requestBody"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/LoginRequest"

    def test_login_responses(self) -> None:
        """Login must define 200, 400, and 401 responses."""
        responses = get_openapi_spec()["paths"]["/api/auth/login"]["post"]["responses"]
        assert "200" in responses
        assert "400" in responses
        assert "401" in responses

    def test_login_200_schema_ref(self) -> None:
        """Login 200 response must reference LoginResponse."""
        schema = (
            get_openapi_spec()["paths"]["/api/auth/login"]["post"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/LoginResponse"

    def test_logout_is_post(self) -> None:
        """POST /api/auth/logout must be defined."""
        path = get_openapi_spec()["paths"]["/api/auth/logout"]
        assert "post" in path

    def test_logout_operation_id(self) -> None:
        """Logout operationId must be 'logout'."""
        op = get_openapi_spec()["paths"]["/api/auth/logout"]["post"]
        assert op["operationId"] == "logout"

    def test_logout_requires_auth(self) -> None:
        """Logout must require BearerAuth."""
        op = get_openapi_spec()["paths"]["/api/auth/logout"]["post"]
        assert {"BearerAuth": []} in op["security"]

    def test_logout_200_schema_ref(self) -> None:
        """Logout 200 must reference SuccessResponse."""
        schema = (
            get_openapi_spec()["paths"]["/api/auth/logout"]["post"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/SuccessResponse"


@pytest.mark.unit
class TestExtensionsEndpoints:
    """Tests for /api/extensions and /api/extensions/{number} paths."""

    def test_list_extensions_is_get(self) -> None:
        """GET /api/extensions must be defined."""
        path = get_openapi_spec()["paths"]["/api/extensions"]
        assert "get" in path

    def test_list_extensions_operation_id(self) -> None:
        """List extensions operationId must be 'getExtensions'."""
        op = get_openapi_spec()["paths"]["/api/extensions"]["get"]
        assert op["operationId"] == "getExtensions"

    def test_list_extensions_requires_auth(self) -> None:
        """List extensions must require BearerAuth."""
        op = get_openapi_spec()["paths"]["/api/extensions"]["get"]
        assert {"BearerAuth": []} in op["security"]

    def test_list_extensions_200_is_array(self) -> None:
        """200 response must be an array of Extensions."""
        schema = (
            get_openapi_spec()["paths"]["/api/extensions"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["type"] == "array"
        assert schema["items"]["$ref"] == "#/components/schemas/Extension"

    def test_create_extension_is_post(self) -> None:
        """POST /api/extensions must be defined."""
        path = get_openapi_spec()["paths"]["/api/extensions"]
        assert "post" in path

    def test_create_extension_operation_id(self) -> None:
        """Create extension operationId must be 'createExtension'."""
        op = get_openapi_spec()["paths"]["/api/extensions"]["post"]
        assert op["operationId"] == "createExtension"

    def test_create_extension_request_body_ref(self) -> None:
        """Create extension request body must reference CreateExtensionRequest."""
        schema = (
            get_openapi_spec()["paths"]["/api/extensions"]["post"]["requestBody"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/CreateExtensionRequest"

    def test_create_extension_responses(self) -> None:
        """Create extension must define 200, 400, 401 responses."""
        responses = get_openapi_spec()["paths"]["/api/extensions"]["post"]["responses"]
        assert "200" in responses
        assert "400" in responses
        assert "401" in responses

    def test_update_extension_is_put(self) -> None:
        """PUT /api/extensions/{number} must be defined."""
        path = get_openapi_spec()["paths"]["/api/extensions/{number}"]
        assert "put" in path

    def test_update_extension_operation_id(self) -> None:
        """Update extension operationId must be 'updateExtension'."""
        op = get_openapi_spec()["paths"]["/api/extensions/{number}"]["put"]
        assert op["operationId"] == "updateExtension"

    def test_update_extension_path_parameter(self) -> None:
        """Update extension must have a required 'number' path parameter."""
        params = get_openapi_spec()["paths"]["/api/extensions/{number}"]["put"]["parameters"]
        assert len(params) == 1
        param = params[0]
        assert param["name"] == "number"
        assert param["in"] == "path"
        assert param["required"] is True
        assert param["schema"]["pattern"] == "^\\d{4}$"

    def test_update_extension_request_body_ref(self) -> None:
        """Update extension request body must reference UpdateExtensionRequest."""
        schema = (
            get_openapi_spec()["paths"]["/api/extensions/{number}"]["put"]["requestBody"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/UpdateExtensionRequest"

    def test_update_extension_responses(self) -> None:
        """Update extension must define 200, 400, 404 responses."""
        responses = get_openapi_spec()["paths"]["/api/extensions/{number}"]["put"]["responses"]
        assert "200" in responses
        assert "400" in responses
        assert "404" in responses

    def test_delete_extension_is_delete(self) -> None:
        """DELETE /api/extensions/{number} must be defined."""
        path = get_openapi_spec()["paths"]["/api/extensions/{number}"]
        assert "delete" in path

    def test_delete_extension_operation_id(self) -> None:
        """Delete extension operationId must be 'deleteExtension'."""
        op = get_openapi_spec()["paths"]["/api/extensions/{number}"]["delete"]
        assert op["operationId"] == "deleteExtension"

    def test_delete_extension_path_parameter(self) -> None:
        """Delete extension must have a required 'number' path parameter."""
        params = get_openapi_spec()["paths"]["/api/extensions/{number}"]["delete"]["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "number"
        assert params[0]["required"] is True

    def test_delete_extension_responses(self) -> None:
        """Delete extension must define 200 and 404 responses."""
        responses = (
            get_openapi_spec()["paths"]["/api/extensions/{number}"]["delete"]["responses"]
        )
        assert "200" in responses
        assert "404" in responses


@pytest.mark.unit
class TestCallsEndpoints:
    """Tests for /api/calls and /api/statistics paths."""

    def test_active_calls_is_get(self) -> None:
        """GET /api/calls must be defined."""
        path = get_openapi_spec()["paths"]["/api/calls"]
        assert "get" in path

    def test_active_calls_operation_id(self) -> None:
        """Active calls operationId must be 'getActiveCalls'."""
        op = get_openapi_spec()["paths"]["/api/calls"]["get"]
        assert op["operationId"] == "getActiveCalls"

    def test_active_calls_requires_auth(self) -> None:
        """Active calls must require BearerAuth."""
        op = get_openapi_spec()["paths"]["/api/calls"]["get"]
        assert {"BearerAuth": []} in op["security"]

    def test_active_calls_200_is_array_of_strings(self) -> None:
        """200 response must be an array of strings."""
        schema = (
            get_openapi_spec()["paths"]["/api/calls"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "string"

    def test_statistics_is_get(self) -> None:
        """GET /api/statistics must be defined."""
        path = get_openapi_spec()["paths"]["/api/statistics"]
        assert "get" in path

    def test_statistics_operation_id(self) -> None:
        """Statistics operationId must be 'getStatistics'."""
        op = get_openapi_spec()["paths"]["/api/statistics"]["get"]
        assert op["operationId"] == "getStatistics"

    def test_statistics_days_query_parameter(self) -> None:
        """Statistics must have an optional 'days' query parameter."""
        params = get_openapi_spec()["paths"]["/api/statistics"]["get"]["parameters"]
        assert len(params) == 1
        param = params[0]
        assert param["name"] == "days"
        assert param["in"] == "query"
        assert param["required"] is False
        assert param["schema"]["type"] == "integer"
        assert param["schema"]["default"] == 7

    def test_statistics_200_schema_properties(self) -> None:
        """Statistics 200 response must include call_quality and real_time."""
        schema = (
            get_openapi_spec()["paths"]["/api/statistics"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert "call_quality" in schema["properties"]
        assert "real_time" in schema["properties"]


@pytest.mark.unit
class TestConfigEndpoints:
    """Tests for /api/config and /api/config/full paths."""

    def test_get_config_is_get(self) -> None:
        """GET /api/config must be defined."""
        path = get_openapi_spec()["paths"]["/api/config"]
        assert "get" in path

    def test_get_config_operation_id(self) -> None:
        """Get config operationId must be 'getConfig'."""
        op = get_openapi_spec()["paths"]["/api/config"]["get"]
        assert op["operationId"] == "getConfig"

    def test_get_config_no_auth_required(self) -> None:
        """GET /api/config must not require authentication."""
        op = get_openapi_spec()["paths"]["/api/config"]["get"]
        assert "security" not in op

    def test_get_config_200_schema_ref(self) -> None:
        """200 response must reference ConfigResponse."""
        schema = (
            get_openapi_spec()["paths"]["/api/config"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        assert schema["$ref"] == "#/components/schemas/ConfigResponse"

    def test_update_config_is_put(self) -> None:
        """PUT /api/config must be defined."""
        path = get_openapi_spec()["paths"]["/api/config"]
        assert "put" in path

    def test_update_config_operation_id(self) -> None:
        """Update config operationId must be 'updateConfig'."""
        op = get_openapi_spec()["paths"]["/api/config"]["put"]
        assert op["operationId"] == "updateConfig"

    def test_update_config_requires_auth(self) -> None:
        """PUT /api/config must require BearerAuth."""
        op = get_openapi_spec()["paths"]["/api/config"]["put"]
        assert {"BearerAuth": []} in op["security"]

    def test_update_config_responses(self) -> None:
        """Update config must define 200, 401, 500 responses."""
        responses = get_openapi_spec()["paths"]["/api/config"]["put"]["responses"]
        assert "200" in responses
        assert "401" in responses
        assert "500" in responses

    def test_full_config_is_get(self) -> None:
        """GET /api/config/full must be defined."""
        path = get_openapi_spec()["paths"]["/api/config/full"]
        assert "get" in path

    def test_full_config_operation_id(self) -> None:
        """Full config operationId must be 'getFullConfig'."""
        op = get_openapi_spec()["paths"]["/api/config/full"]["get"]
        assert op["operationId"] == "getFullConfig"

    def test_full_config_requires_auth(self) -> None:
        """GET /api/config/full must require BearerAuth."""
        op = get_openapi_spec()["paths"]["/api/config/full"]["get"]
        assert {"BearerAuth": []} in op["security"]

    def test_full_config_responses(self) -> None:
        """Full config must define 200 and 401 responses."""
        responses = get_openapi_spec()["paths"]["/api/config/full"]["get"]["responses"]
        assert "200" in responses
        assert "401" in responses


@pytest.mark.unit
class TestComponentsSecuritySchemes:
    """Tests for the security schemes in the components section."""

    def test_bearer_auth_scheme_present(self) -> None:
        """BearerAuth security scheme must be defined."""
        schemes = get_openapi_spec()["components"]["securitySchemes"]
        assert "BearerAuth" in schemes

    def test_bearer_auth_type(self) -> None:
        """BearerAuth type must be 'http'."""
        scheme = get_openapi_spec()["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["type"] == "http"

    def test_bearer_auth_scheme_value(self) -> None:
        """BearerAuth scheme must be 'bearer'."""
        scheme = get_openapi_spec()["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["scheme"] == "bearer"

    def test_bearer_auth_has_description(self) -> None:
        """BearerAuth must have a description."""
        scheme = get_openapi_spec()["components"]["securitySchemes"]["BearerAuth"]
        assert "description" in scheme
        assert len(scheme["description"]) > 0


@pytest.mark.unit
class TestComponentsSchemas:
    """Tests for all schemas defined in the components section."""

    def test_all_expected_schemas_present(self) -> None:
        """All referenced schemas must be defined."""
        schemas = get_openapi_spec()["components"]["schemas"]
        expected = [
            "Error",
            "SuccessResponse",
            "HealthResponse",
            "LoginRequest",
            "LoginResponse",
            "Extension",
            "CreateExtensionRequest",
            "UpdateExtensionRequest",
            "ConfigResponse",
        ]
        for name in expected:
            assert name in schemas, f"Missing schema: {name}"

    def test_schema_count(self) -> None:
        """Verify the total number of schemas."""
        schemas = get_openapi_spec()["components"]["schemas"]
        assert len(schemas) == 9

    def test_error_schema_structure(self) -> None:
        """Error schema must have required 'error' string property."""
        schema = get_openapi_spec()["components"]["schemas"]["Error"]
        assert schema["type"] == "object"
        assert "error" in schema["properties"]
        assert schema["properties"]["error"]["type"] == "string"
        assert "error" in schema["required"]

    def test_success_response_schema(self) -> None:
        """SuccessResponse must have 'success' boolean and optional 'message'."""
        schema = get_openapi_spec()["components"]["schemas"]["SuccessResponse"]
        assert schema["type"] == "object"
        assert schema["properties"]["success"]["type"] == "boolean"
        assert schema["properties"]["message"]["type"] == "string"
        assert "success" in schema["required"]

    def test_health_response_schema(self) -> None:
        """HealthResponse must have status enum."""
        schema = get_openapi_spec()["components"]["schemas"]["HealthResponse"]
        assert schema["type"] == "object"
        status = schema["properties"]["status"]
        assert status["type"] == "string"
        assert status["enum"] == ["ready", "not_ready", "error"]

    def test_login_request_schema(self) -> None:
        """LoginRequest must require extension and password."""
        schema = get_openapi_spec()["components"]["schemas"]["LoginRequest"]
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"extension", "password"}
        assert schema["properties"]["extension"]["type"] == "string"
        assert schema["properties"]["password"]["type"] == "string"

    def test_login_response_schema(self) -> None:
        """LoginResponse must require success, token, extension."""
        schema = get_openapi_spec()["components"]["schemas"]["LoginResponse"]
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"success", "token", "extension"}
        assert "is_admin" in schema["properties"]
        assert "name" in schema["properties"]
        assert "email" in schema["properties"]

    def test_extension_schema(self) -> None:
        """Extension schema must define all expected properties."""
        schema = get_openapi_spec()["components"]["schemas"]["Extension"]
        assert schema["type"] == "object"
        expected_props = {
            "number", "name", "email", "registered",
            "allow_external", "ad_synced", "is_admin",
        }
        assert expected_props == set(schema["properties"].keys())
        assert set(schema["required"]) == {"number", "name"}

    def test_extension_email_nullable(self) -> None:
        """Extension email must be nullable."""
        schema = get_openapi_spec()["components"]["schemas"]["Extension"]
        assert schema["properties"]["email"]["nullable"] is True

    def test_extension_email_format(self) -> None:
        """Extension email must use email format."""
        schema = get_openapi_spec()["components"]["schemas"]["Extension"]
        assert schema["properties"]["email"]["format"] == "email"

    def test_create_extension_request_schema(self) -> None:
        """CreateExtensionRequest must require number, name, password, voicemail_pin."""
        schema = get_openapi_spec()["components"]["schemas"]["CreateExtensionRequest"]
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"number", "name", "password", "voicemail_pin"}

    def test_create_extension_number_pattern(self) -> None:
        """CreateExtensionRequest number must have pattern ^\\d{4}$."""
        props = get_openapi_spec()["components"]["schemas"]["CreateExtensionRequest"]["properties"]
        assert props["number"]["pattern"] == "^\\d{4}$"

    def test_create_extension_password_min_length(self) -> None:
        """CreateExtensionRequest password must have minLength 8."""
        props = get_openapi_spec()["components"]["schemas"]["CreateExtensionRequest"]["properties"]
        assert props["password"]["minLength"] == 8

    def test_create_extension_voicemail_pin_pattern(self) -> None:
        """CreateExtensionRequest voicemail_pin must have pattern ^\\d{4,6}$."""
        props = get_openapi_spec()["components"]["schemas"]["CreateExtensionRequest"]["properties"]
        assert props["voicemail_pin"]["pattern"] == "^\\d{4,6}$"

    def test_create_extension_defaults(self) -> None:
        """CreateExtensionRequest must have correct defaults for boolean fields."""
        props = get_openapi_spec()["components"]["schemas"]["CreateExtensionRequest"]["properties"]
        assert props["allow_external"]["default"] is True
        assert props["is_admin"]["default"] is False

    def test_update_extension_request_schema(self) -> None:
        """UpdateExtensionRequest must have all optional fields."""
        schema = get_openapi_spec()["components"]["schemas"]["UpdateExtensionRequest"]
        assert schema["type"] == "object"
        assert "required" not in schema
        expected_props = {
            "name", "email", "password", "voicemail_pin",
            "allow_external", "is_admin",
        }
        assert expected_props == set(schema["properties"].keys())

    def test_update_extension_password_min_length(self) -> None:
        """UpdateExtensionRequest password must have minLength 8."""
        props = get_openapi_spec()["components"]["schemas"]["UpdateExtensionRequest"]["properties"]
        assert props["password"]["minLength"] == 8

    def test_config_response_schema(self) -> None:
        """ConfigResponse must have smtp, email, email_notifications, integrations."""
        schema = get_openapi_spec()["components"]["schemas"]["ConfigResponse"]
        assert schema["type"] == "object"
        expected_props = {"smtp", "email", "email_notifications", "integrations"}
        assert expected_props == set(schema["properties"].keys())

    def test_config_response_smtp_properties(self) -> None:
        """ConfigResponse smtp must have host, port, username."""
        smtp = get_openapi_spec()["components"]["schemas"]["ConfigResponse"]["properties"]["smtp"]
        assert smtp["type"] == "object"
        assert "host" in smtp["properties"]
        assert "port" in smtp["properties"]
        assert "username" in smtp["properties"]

    def test_config_response_email_properties(self) -> None:
        """ConfigResponse email must have from_address."""
        email = get_openapi_spec()["components"]["schemas"]["ConfigResponse"]["properties"]["email"]
        assert email["type"] == "object"
        assert "from_address" in email["properties"]


@pytest.mark.unit
class TestOpenAPIOperationIds:
    """Verify that every operation has a unique operationId."""

    def test_all_operation_ids_unique(self) -> None:
        """All operationId values must be unique across the spec."""
        spec = get_openapi_spec()
        operation_ids: list[str] = []
        for _path, methods in spec["paths"].items():
            for _method, operation in methods.items():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation_ids.append(operation["operationId"])
        assert len(operation_ids) == len(set(operation_ids))

    def test_expected_operation_ids(self) -> None:
        """All expected operationIds must be present."""
        spec = get_openapi_spec()
        operation_ids: set[str] = set()
        for _path, methods in spec["paths"].items():
            for _method, operation in methods.items():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation_ids.add(operation["operationId"])

        expected = {
            "healthCheck", "detailedHealth", "getStatus",
            "login", "logout",
            "getExtensions", "createExtension", "updateExtension", "deleteExtension",
            "getActiveCalls", "getStatistics",
            "getConfig", "updateConfig", "getFullConfig",
        }
        assert expected == operation_ids


@pytest.mark.unit
class TestOpenAPISchemaRefs:
    """Tests validating that all $ref values point to existing schemas."""

    def _collect_refs(self, obj: Any) -> list[str]:
        """Recursively collect all $ref values from a nested dict/list."""
        refs: list[str] = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    refs.append(value)
                else:
                    refs.extend(self._collect_refs(value))
        elif isinstance(obj, list):
            for item in obj:
                refs.extend(self._collect_refs(item))
        return refs

    def test_all_refs_resolve(self) -> None:
        """Every $ref in the spec must resolve to a defined schema."""
        spec = get_openapi_spec()
        refs = self._collect_refs(spec["paths"])
        schemas = spec["components"]["schemas"]
        for ref in refs:
            prefix = "#/components/schemas/"
            assert ref.startswith(prefix), f"Unexpected ref prefix: {ref}"
            schema_name = ref[len(prefix):]
            assert schema_name in schemas, f"Unresolved $ref: {ref}"


@pytest.mark.unit
class TestOpenAPISecurityAnnotations:
    """Tests that security annotations are correctly applied across endpoints."""

    def test_unauthenticated_endpoints(self) -> None:
        """Certain endpoints must NOT require authentication."""
        spec = get_openapi_spec()
        # /health GET and /api/config GET should be public
        health_op = spec["paths"]["/health"]["get"]
        config_op = spec["paths"]["/api/config"]["get"]
        assert "security" not in health_op
        assert "security" not in config_op

    def test_authenticated_endpoints(self) -> None:
        """Endpoints that modify state or return sensitive data must require auth."""
        spec = get_openapi_spec()
        secured_operations = [
            ("/api/auth/logout", "post"),
            ("/api/extensions", "get"),
            ("/api/extensions", "post"),
            ("/api/extensions/{number}", "put"),
            ("/api/extensions/{number}", "delete"),
            ("/api/calls", "get"),
            ("/api/statistics", "get"),
            ("/api/config", "put"),
            ("/api/config/full", "get"),
        ]
        for path, method in secured_operations:
            op = spec["paths"][path][method]
            assert "security" in op, f"{method.upper()} {path} missing security"
            assert {"BearerAuth": []} in op["security"], (
                f"{method.upper()} {path} missing BearerAuth"
            )
