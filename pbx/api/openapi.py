"""OpenAPI 3.0 specification for the PBX API.

Provides a complete API specification documenting all endpoints,
request/response schemas, and authentication requirements.
"""


def get_openapi_spec():
    """Return the OpenAPI 3.0 specification as a dictionary.

    Returns:
        dict: Complete OpenAPI 3.0 specification for the PBX API.
    """
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "PBX API",
            "description": (
                "REST API for the PBX system. Provides endpoints for managing "
                "extensions, calls, configuration, voicemail, and system health."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "PBX Admin",
            },
            "license": {
                "name": "Proprietary",
            },
        },
        "servers": [
            {
                "url": "/",
                "description": "Current server",
            }
        ],
        "tags": [
            {"name": "Health", "description": "Health check and monitoring endpoints"},
            {"name": "Auth", "description": "Authentication endpoints"},
            {"name": "Extensions", "description": "Extension management (CRUD)"},
            {"name": "Calls", "description": "Call management and analytics"},
            {"name": "Config", "description": "System configuration management"},
        ],
        "paths": {
            # --- Health endpoints ---
            "/health": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Health check",
                    "description": (
                        "Lightweight health check for container orchestration. "
                        "Returns readiness status."
                    ),
                    "operationId": "healthCheck",
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthResponse"
                                    }
                                }
                            },
                        },
                        "503": {
                            "description": "Service is unhealthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/api/health/detailed": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Detailed health status",
                    "description": "Comprehensive health status for monitoring dashboards.",
                    "operationId": "detailedHealth",
                    "responses": {
                        "200": {
                            "description": "Detailed health information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "overall_status": {
                                                "type": "string",
                                                "enum": ["healthy", "degraded", "unhealthy"],
                                            },
                                            "components": {
                                                "type": "object",
                                                "additionalProperties": True,
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "503": {
                            "description": "Service is unhealthy",
                        },
                    },
                }
            },
            "/api/status": {
                "get": {
                    "tags": ["Health"],
                    "summary": "PBX status",
                    "description": "Get overall PBX system status.",
                    "operationId": "getStatus",
                    "responses": {
                        "200": {
                            "description": "PBX status information",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        },
                        "500": {
                            "description": "PBX not initialized",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            # --- Auth endpoints ---
            "/api/auth/login": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Login",
                    "description": (
                        "Authenticate an extension using its voicemail PIN. "
                        "Returns a session token on success."
                    ),
                    "operationId": "login",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/LoginRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Login successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/LoginResponse"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Missing required fields",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Invalid credentials",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/api/auth/logout": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Logout",
                    "description": (
                        "Logout the current session. Primarily handled client-side "
                        "by removing the token."
                    ),
                    "operationId": "logout",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Logout successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SuccessResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            # --- Extensions endpoints ---
            "/api/extensions": {
                "get": {
                    "tags": ["Extensions"],
                    "summary": "list extensions",
                    "description": (
                        "Get all extensions. Admin users see all extensions; "
                        "non-admin users see only their own."
                    ),
                    "operationId": "getExtensions",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "list of extensions",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/Extension"
                                        },
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Authentication required",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                },
                "post": {
                    "tags": ["Extensions"],
                    "summary": "Create extension",
                    "description": "Add a new extension. Requires admin privileges.",
                    "operationId": "createExtension",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CreateExtensionRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Extension created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SuccessResponse"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Validation error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Admin authentication required",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                },
            },
            "/api/extensions/{number}": {
                "put": {
                    "tags": ["Extensions"],
                    "summary": "Update extension",
                    "description": "Update an existing extension. Requires admin privileges.",
                    "operationId": "updateExtension",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "number",
                            "in": "path",
                            "required": True,
                            "description": "4-digit extension number",
                            "schema": {"type": "string", "pattern": "^\\d{4}$"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/UpdateExtensionRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Extension updated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SuccessResponse"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Validation error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "Extension not found",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                },
                "delete": {
                    "tags": ["Extensions"],
                    "summary": "Delete extension",
                    "description": "Delete an extension. Requires admin privileges.",
                    "operationId": "deleteExtension",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "number",
                            "in": "path",
                            "required": True,
                            "description": "4-digit extension number",
                            "schema": {"type": "string", "pattern": "^\\d{4}$"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Extension deleted",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SuccessResponse"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "Extension not found",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            },
                        },
                    },
                },
            },
            # --- Calls endpoints ---
            "/api/calls": {
                "get": {
                    "tags": ["Calls"],
                    "summary": "list active calls",
                    "description": "Get all currently active calls.",
                    "operationId": "getActiveCalls",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "list of active calls",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Authentication required",
                        },
                    },
                }
            },
            "/api/statistics": {
                "get": {
                    "tags": ["Calls"],
                    "summary": "Dashboard statistics",
                    "description": "Get comprehensive statistics for the dashboard.",
                    "operationId": "getStatistics",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "days",
                            "in": "query",
                            "required": False,
                            "description": "Number of days to include (default: 7)",
                            "schema": {"type": "integer", "default": 7},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Dashboard statistics",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "call_quality": {"type": "object"},
                                            "real_time": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        },
                    },
                }
            },
            # --- Config endpoints ---
            "/api/config": {
                "get": {
                    "tags": ["Config"],
                    "summary": "Get configuration",
                    "description": (
                        "Get current configuration. Returns a default config "
                        "structure for non-authenticated users to allow "
                        "graceful UI loading."
                    ),
                    "operationId": "getConfig",
                    "responses": {
                        "200": {
                            "description": "Configuration data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ConfigResponse"
                                    }
                                }
                            },
                        },
                    },
                },
                "put": {
                    "tags": ["Config"],
                    "summary": "Update configuration",
                    "description": "Update system configuration. Requires admin privileges.",
                    "operationId": "updateConfig",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Configuration updated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SuccessResponse"
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Admin authentication required",
                        },
                        "500": {
                            "description": "Update failed",
                        },
                    },
                },
            },
            "/api/config/full": {
                "get": {
                    "tags": ["Config"],
                    "summary": "Get full configuration",
                    "description": (
                        "Get comprehensive system configuration for the admin panel. "
                        "Requires admin privileges."
                    ),
                    "operationId": "getFullConfig",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Full configuration data",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        },
                        "401": {
                            "description": "Admin authentication required",
                        },
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "Session token obtained from /api/auth/login. "
                        "Pass as: Authorization: Bearer <token>"
                    ),
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message",
                        }
                    },
                    "required": ["error"],
                },
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "message": {"type": "string"},
                    },
                    "required": ["success"],
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["ready", "not_ready", "error"],
                        },
                    },
                },
                "LoginRequest": {
                    "type": "object",
                    "properties": {
                        "extension": {
                            "type": "string",
                            "description": "4-digit extension number",
                            "example": "1001",
                        },
                        "password": {
                            "type": "string",
                            "description": "Voicemail PIN",
                            "example": "1234",
                        },
                    },
                    "required": ["extension", "password"],
                },
                "LoginResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "token": {
                            "type": "string",
                            "description": "Session token for authenticated requests",
                        },
                        "extension": {"type": "string"},
                        "is_admin": {"type": "boolean"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["success", "token", "extension"],
                },
                "Extension": {
                    "type": "object",
                    "description": "Extension details as returned by the API",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "4-digit extension number",
                            "example": "1001",
                        },
                        "name": {
                            "type": "string",
                            "description": "Display name",
                            "example": "John Doe",
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "nullable": True,
                        },
                        "registered": {
                            "type": "boolean",
                            "description": "Whether the extension is currently registered",
                        },
                        "allow_external": {
                            "type": "boolean",
                            "description": "Whether external calls are allowed",
                        },
                        "ad_synced": {
                            "type": "boolean",
                            "description": "Whether synced from Active Directory",
                        },
                        "is_admin": {
                            "type": "boolean",
                            "description": "Whether the extension has admin privileges",
                        },
                    },
                    "required": ["number", "name"],
                },
                "CreateExtensionRequest": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "4-digit extension number",
                            "pattern": "^\\d{4}$",
                            "example": "1001",
                        },
                        "name": {
                            "type": "string",
                            "description": "Display name",
                            "example": "John Doe",
                        },
                        "password": {
                            "type": "string",
                            "description": "SIP password (min 8 characters)",
                            "minLength": 8,
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "description": "Email address (optional)",
                        },
                        "voicemail_pin": {
                            "type": "string",
                            "description": "Voicemail PIN (4-6 digits, required)",
                            "pattern": "^\\d{4,6}$",
                            "example": "1234",
                        },
                        "allow_external": {
                            "type": "boolean",
                            "default": True,
                        },
                        "is_admin": {
                            "type": "boolean",
                            "default": False,
                        },
                    },
                    "required": ["number", "name", "password", "voicemail_pin"],
                },
                "UpdateExtensionRequest": {
                    "type": "object",
                    "description": "All fields are optional; only provided fields are updated.",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "password": {
                            "type": "string",
                            "description": "New SIP password (min 8 characters)",
                            "minLength": 8,
                        },
                        "voicemail_pin": {
                            "type": "string",
                            "description": "New voicemail PIN (4-6 digits)",
                            "pattern": "^\\d{4,6}$",
                        },
                        "allow_external": {"type": "boolean"},
                        "is_admin": {"type": "boolean"},
                    },
                },
                "ConfigResponse": {
                    "type": "object",
                    "description": "System configuration subset",
                    "properties": {
                        "smtp": {
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "port": {"type": "integer"},
                                "username": {"type": "string"},
                            },
                        },
                        "email": {
                            "type": "object",
                            "properties": {
                                "from_address": {"type": "string"},
                            },
                        },
                        "email_notifications": {"type": "boolean"},
                        "integrations": {"type": "object"},
                    },
                },
            },
        },
    }
