import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
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

mcp = FastMCP("MCP Server with AUTH", auth=auth_helper.bearer_auth)
mcp.add_middleware(AuthorizationMiddleware(auth_helper))
# mcp.add_middleware(LoggingMiddleware())

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