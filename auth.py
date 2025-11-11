"""
Azure Authentication Module for FastAPI

This module configures Azure Active Directory (Azure AD) authentication for a FastAPI application
using the fastapi-azure-auth library. It sets up single-tenant OAuth2 authorization code flow
with bearer token authentication.

Environment Variables Required:
    TENANT_ID: Azure AD tenant identifier
    API_CLIENT_ID: Azure AD application (client) ID for the API
    API_SCOPES: JSON string containing the OAuth2 scopes for the API

Example .env file:
    TENANT_ID=your-tenant-id-here
    API_CLIENT_ID=your-api-client-id-here
    API_SCOPES=["api://your-api-id/access_as_user"]

Usage:
    from src.api.auth import azure_scheme
    
    # Use as dependency in FastAPI routes
    @app.get("/protected")
    async def protected_route(user=Depends(azure_scheme)):
        return {"user": user}
"""

# Standard library imports
import json
import logging
from os import environ

# Third-party imports
import dotenv
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

# Load environment variables from .env file located in parent directory
dotenv.load_dotenv(".env")

# Configure logger for this module
logger = logging.getLogger(__name__)

# Load Azure AD configuration from environment variables
tenant_id = environ.get("AUTH_TENANT_ID")
client_id = environ.get("API_CLIENT_ID")

# Parse scopes from JSON string in environment variable
# Expected format: ["scope1", "scope2", ...] as JSON string
try:
    scopes = json.loads(environ.get("API_SCOPES", "[]"))
except (json.JSONDecodeError, TypeError) as e:
    logger.error(f"Failed to parse API_SCOPES from environment: {e}")
    scopes = []

# Log configuration for debugging (be careful with sensitive information in production)
logger.info(f"Tenant ID: {tenant_id}")
logger.info(f"API Client ID: {client_id}")
logger.info(f"Scopes: {scopes}")

# Validate required configuration
if not tenant_id:
    raise ValueError("TENANT_ID environment variable is required")
if not client_id:
    raise ValueError("API_CLIENT_ID environment variable is required")
if not scopes:
    logger.warning("No scopes configured - API may not function correctly")

# Initialize Azure AD authentication scheme
# This creates a FastAPI dependency that can be used to protect routes
azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=client_id,
    tenant_id=tenant_id,
    scopes=scopes,
)