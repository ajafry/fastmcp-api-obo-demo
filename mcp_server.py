import logging
import os
import jwt
import requests
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.auth.providers.jwt import JWTVerifier  # Used for Tier-1 JWT token validation
# from shared.middleware.authorization_middleware import AuthorizationMiddleware  # Role-based filtering
from fastmcp.server.dependencies import get_access_token, AccessToken

load_dotenv()

TENANT_ID = os.getenv("AUTH_TENANT_ID")
logger = logging.getLogger(__name__)

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

bearer_auth = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
        issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",  # v2.0 format
    )
mcp = FastMCP("MCP Server with AUTH", auth=bearer_auth)

@mcp.tool(tags={"user"})
async def add(a: float, b: float) -> float:
    """
    Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    access_token: AccessToken = get_access_token()
    token_info = jwt.decode(access_token.token, options={"verify_signature": True},
                    algorithms=["RS256"])
    role_access = any(
        role
        for role in token_info.get("roles", [])
        if role in ("user")
    )
    if not role_access:
        return {
            "error": "Access denied. You do not have permission to call this tool."
        }
    result = a + b
    return result

@mcp.tool(tags={"user"})
async def subtract(a: float, b: float) -> float:
    """
    Subtract the second number from the first number.
    
    Args:
        a: First number (minuend)
        b: Second number (subtrahend)
        
    Returns:
        The difference of a and b (a - b)
    """
    logger.info("getting access token...")
    access_token: AccessToken = get_access_token()
    logger.info(f"Access Token: {access_token}")
    token_info = jwt.decode(access_token.token, options={"verify_signature": False})
    logger.info(f"Token Info: {token_info}")
    role_access = any(
        role
        for role in token_info.get("roles", [])
        if role in ("superuser")
    )
    if not role_access:
        return {
            "error": "Access denied. You do not have permission to call the SUBTRACT tool."
        }
    result = a - b
    return result

if __name__ == "__main__":
    # Run the server directly using FastMCP's run method with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001
    )