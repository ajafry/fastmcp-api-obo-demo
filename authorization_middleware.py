from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from starlette.requests import Request
from fastmcp.server.dependencies import get_access_token, AccessToken, get_http_request, get_http_headers
import logging
import jwt
from auth_helper import AuthHelper

class AuthorizationMiddleware(Middleware):
    def __init__(self, auth_helper: AuthHelper):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.auth_helper = auth_helper

    async def on_request(self, context: MiddlewareContext, call_next):
        self.logger.info(f"===>[on_request]")
        token_info = await self.auth_helper.get_token_info()
        self.roles = set(token_info.get("roles", []))
        self.logger.info(f"[on_request] User roles from token: {self.roles}")
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        self.logger.info(f"===>[on_list_tools]")
        result = await call_next(context)
        filtered_tools = []
        for role in self.roles:
            self.logger.info(f"User role being checked: {role}")
            filtered_tools.extend([t for t in result if role in t.tags])

        available_tool_names = [tool.name for tool in filtered_tools]

        if context.fastmcp_context:
            try:
                tool_manager = context.fastmcp_context.fastmcp._tool_manager
                for tool in result:
                    if tool.name not in available_tool_names:
                        self.logger.info(f"AuthorizationMiddleware: Removing tool: --{tool.name}")
                        tool_manager.remove_tool(tool.name)
            except Exception as e:
                self.logger.error(f"Tool manager sync error: {str(e)}")
        return filtered_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        self.logger.info(f"===>[on_call_tool]")
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                allowed_roles = set(tool.tags)
                is_allowed = await self.auth_helper.is_role_allowed(self.roles, allowed_roles)
                self.logger.info(f"[{__name__}]: User roles: {self.roles}, Required roles for tool '{tool.name}': {allowed_roles}, is_allowed: {is_allowed}")
                print(f"Calling tool: {tool.name} with args: {context.message.args}")
            except Exception as e:
                self.logger.error(f"Error in on_call_tool: {str(e)}")
        return await call_next(context)