from dotenv import load_dotenv
import uvicorn
import logging
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi_azure_auth.user import User
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
import os
import requests
from os import environ
from auth import azure_scheme

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print(os.getenv("API_CLIENT_ID"))

app = FastAPI(
    swagger_ui_oauth2_redirect_url='/oauth2-redirect',
    swagger_ui_init_oauth={
        'usePkceWithAuthorizationCodeGrant': True,
        'clientId': environ.get("API_CLIENT_ID"),
        'scopes': environ.get("API_SCOPES")
    },
)

def get_env_config(var_name: str) -> str:
    """Helper function to get environment variable or log an error if not found."""
    value = environ.get(var_name)
    if value is None:
        logger.error(f"Environment variable {var_name} is not set.")
    return value

logger.info(f"=-=-=-=-=-=-=-=-=-=-=-=-=-=-= FastAPI Backend Server =-=-=-=-=-=-=-=-=")
logger.info(f"API Client ID is: {get_env_config('API_CLIENT_ID')}")
#logger.info(f"Front-end Client ID is: {environ.get('FE_CLIENT_ID')}")
logger.info(f"Tenant Id is: {get_env_config('AUTH_TENANT_ID')}")
logger.info(f"API Scopes are: {get_env_config('API_SCOPES')}")
logger.info(f"MCP_SCOPES are: {get_env_config('MCP_SCOPES')}")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== OBO Exchange Logic ==========
async def exchange_token(original_token: str, scope: str) -> dict:
    obo_url = f"https://login.microsoftonline.com/{get_env_config('AUTH_TENANT_ID')}/oauth2/v2.0/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id": f"{get_env_config('API_CLIENT_ID')}",
        "client_secret": f"{get_env_config('API_SECRET')}",
        "assertion": original_token,
        "scope": scope,
        "requested_token_use": "on_behalf_of",
    }
    try:
        response = requests.post(obo_url, data=data)
        if response.status_code == 200:
            return {"success": True, "access_token": response.json()["access_token"]}
        return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_headers(user: User) -> dict:
    user_token = user.access_token
    logger.info(f"=====>>> User Token: {user_token}")
    obo_token = await exchange_token(user_token, get_env_config("MCP_SCOPES"))
    logger.info(f"*****>>> OBO Token: {obo_token}")
    headers = {"Authorization": f"Bearer {obo_token['access_token']}"}
    return headers

# Simple API endpoints
@app.get("/hello/{name}")
async def hello(name: str):
    """
    Simple hello endpoint that greets a user by name.
    
    Args:
        name (str): The name to greet
        
    Returns:
        dict: A greeting message
    """
    return {"message": f"Hello {name}"}

@app.get("/add/{num1}/{num2}")
async def add_numbers(num1: float, num2: float, user: User = Security(azure_scheme)):
    """
    Simple addition endpoint that adds two numbers.
    
    Args:
        num1 (float): First number
        num2 (float): Second number
        
    Returns:
        dict: The sum of the two numbers
    """
    # result = num1 + num2

    user_token = user.access_token
    logger.info(f"=====>>> User Token: {user_token}")
    obo_token = await exchange_token(user_token, get_env_config("MCP_SCOPES"))
    logger.info(f"*****>>> OBO Token: {obo_token}")


    headers = {"Authorization": f"Bearer {obo_token['access_token']}"}
    logger.info(f"Headers: {headers}")
    
    mcp_client = Client(StreamableHttpTransport(
        os.getenv("MCP_SERVER_URL"),
        headers=headers
    ))
    try:
        async with mcp_client:
            result = await mcp_client.call_tool("add", {"a": num1, "b": num2})
    except Exception as e:
        print(f"Error calling add: {e}")
        return {"error": str(e)}

    return {"sum": result}

@app.get("/subtract/{num1}/{num2}")
async def subtract_numbers(num1: float, num2: float, user: User = Security(azure_scheme)):
    """
    Simple subtraction endpoint that subtracts two numbers.
    
    Args:
        num1 (float): First number
        num2 (float): Second number
        
    Returns:
        dict: The difference of the two numbers
    """    
    mcp_client = Client(StreamableHttpTransport(
        os.getenv("MCP_SERVER_URL"),
        headers=await get_headers(user)
    ))
    try:
        async with mcp_client:
            result = await mcp_client.call_tool("subtract", {"a": num1, "b": num2})
    except Exception as e:
        print(f"Error calling subtract: {e}")
        return {"error": str(e)}

    return {"difference": result}

@app.get("/multiply/{num1}/{num2}")
async def multiply_numbers(num1: float, num2: float, user: User = Security(azure_scheme)):
    """
    Simple multiplication endpoint that multiplies two numbers.
    
    Args:
        num1 (float): First number
        num2 (float): Second number
        
    Returns:
        dict: The product of the two numbers
    """    
    mcp_client = Client(StreamableHttpTransport(
        os.getenv("MCP_SERVER_URL"),
        headers=await get_headers(user)
    ))
    try:
        async with mcp_client:
            result = await mcp_client.call_tool("multiply", {"a": num1, "b": num2})
    except Exception as e:
        print(f"Error calling multiply: {e}")
        return {"error": str(e)}

    return {"product": result}

@app.get("/mcp/", dependencies=[Security(azure_scheme)])
async def call_mcp():
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)