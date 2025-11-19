import logging
import os
import jwt
from jwt import PyJWKClient
from functools import wraps
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
jwks_client = PyJWKClient(f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys")
mcp = FastMCP("MCP Server with AUTH", auth=bearer_auth)

async def get_token_info():
    access_token: AccessToken = get_access_token()
    signing_key = jwks_client.get_signing_key_from_jwt(access_token.token)
    token_info = jwt.decode(
        access_token.token, 
        signing_key.key,
        algorithms=["RS256"],
        audience=f"{os.getenv("MCP_CLIENT_ID")}",
        issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        options={"verify_signature": True}
    )
    return token_info

async def is_role_available(token_info, required_role) :
    return any(
        r
        for r in token_info.get("roles", [])
        if r == required_role
    )

def require_role(required_role: str):
    """
    Decorator that enforces role-based access control for MCP tools.
    
    Args:
        required_role: The role required to access the decorated function
        
    Returns:
        Decorated function that checks authorization before execution
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.info(f"[MCP] Checking authorization for role: {required_role}")
                
                # Get and validate token
                token_info = await get_token_info()
                
                # Check role access
                role_access = await is_role_available(token_info, required_role)
                
                if not role_access:
                    raise PermissionError(f"Access denied. Required role: {required_role}")
                
                # If authorized, execute the original function
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[MCP] Authorization error in {func.__name__}: {e}")
                return {
                    "error": f"Authorization failed: {str(e)}"
                }
        
        return wrapper
    return decorator

@mcp.tool(tags={"user"})
@require_role("user")
async def add(a: float, b: float) -> float:
    """
    Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    logger.info(f"[MCP] getting access token...")
    result = a + b
    return result

@mcp.tool(tags={"user"})
@require_role("superusers")
async def subtract(a: float, b: float) -> float:
    """
    Subtract the second number from the first number.
    
    Args:
        a: First number (minuend)
        b: Second number (subtrahend)
        
    Returns:
        The difference of a and b (a - b)
    """
    result = a - b
    return result

if __name__ == "__main__":
    # Run the server directly using FastMCP's run method with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001
    )