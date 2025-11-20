import logging
import os
import jwt
from jwt import PyJWKClient
from functools import wraps
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
import logging
from fastmcp.server.auth.providers.jwt import JWTVerifier  # Used for Tier-1 JWT token validation
# from shared.middleware.authorization_middleware import AuthorizationMiddleware  # Role-based filtering
from fastmcp.server.dependencies import get_access_token, AccessToken

from authorization_middleware import AuthorizationMiddleware
from auth_helper import AuthHelper

load_dotenv()

TENANT_ID = os.getenv("AUTH_TENANT_ID")
MCP_CLIENT_ID = os.getenv("MCP_CLIENT_ID")
MCP_SECRET = os.getenv("MCP_SECRET")
AUDIENCE = os.getenv("MCP_CLIENT_ID")

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

auth_helper = AuthHelper(
    tenant_id=TENANT_ID,
    client_id=MCP_CLIENT_ID,
    client_secret=MCP_SECRET,
    audience=AUDIENCE
)

bearer_auth = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
        issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",  # v2.0 format
        audience=AUDIENCE
    )
jwks_client = PyJWKClient(f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys")
mcp = FastMCP("MCP Server with AUTH", auth=bearer_auth)
# mcp.add_middleware(LoggingMiddleware())
# mcp.add_middleware(AuthorizationMiddleware(bearer_auth))
mcp.add_middleware(AuthorizationMiddleware(auth_helper))
# mcp = FastMCP("MCP Server with AUTH", auth=auth_context.bearer_auth)

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
    # token_info = jwt.decode(
    #     access_token.token, 
    #     algorithms=["RS256"],
    #     options={"verify_signature": True})

    return token_info

async def is_role_allowed(token_info, required_roles) :
    return len(required_roles & set(token_info.get("roles", []))) > 0
    # return any(
    #     r
    #     for r in token_info.get("roles", [])
    #     if r in required_roles
    # )

def require_roles(required_roles: set):
    """
    Decorator that enforces role-based access control for MCP tools.
    
    Args:
        required_roles: The roles required to access the decorated function
        
    Returns:
        Decorated function that checks authorization before execution
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.info(f"[MCP] Checking authorization for role: {required_roles}")
                
                # Get and validate token
                token_info = await get_token_info()
                
                # Check role access
                role_access = await is_role_allowed(token_info, required_roles)
                
                if not role_access:
                    raise PermissionError(f"Access denied. Required role: {required_roles}")
                
                # If authorized, execute the original function
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[MCP] Authorization error in {func.__name__}: {e}")
                return {
                    "error": f"Authorization failed: {str(e)}"
                }
        
        return wrapper
    return decorator

@mcp.tool(tags={"user", "superuser"})
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

@mcp.tool(tags={"superuser"})
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

@mcp.tool(tags={"outofthisworlduser", "user"})
async def multiply(a: float, b: float) -> float:
    """
    Multiply the first number with the second number.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The product of a and b
    """
    result = a * b
    return result

if __name__ == "__main__":
    # Run the server directly using FastMCP's run method with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001
    )