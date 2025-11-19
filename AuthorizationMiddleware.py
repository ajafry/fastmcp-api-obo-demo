from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from starlette.requests import Request
from fastmcp.server.dependencies import get_access_token, AccessToken, get_http_request, get_http_headers
import jwt

class AuthorizationMiddleware(Middleware):
    def __init__(self, auth_context, redis_token_store=None):
        self.auth_context = auth_context
        self.redis_token_store = redis_token_store

    async def on_request(self, context: MiddlewareContext, call_next):
        access_token: AccessToken = get_access_token().token
        self.claims = jwt.decode(access_token, options={"verify_signature": False})
        self.roles = self.claims.get('roles')
        self.user_id = self.claims.get('upn')
        self.oid = self.claims.get('oid')
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        filtered_tools = []
        for role in self.roles:
            if role == 'Task.Write':
                filtered_tools.extend([t for t in result if "write" in t.tags])
            if role == 'Task.Read':
                filtered_tools.extend([t for t in result if "read" in t.tags])
            if role == 'Task.All':
                filtered_tools = result

        available_tool_names = [tool.name for tool in filtered_tools]

        if context.fastmcp_context:
            try:
                tool_manager = context.fastmcp_context.fastmcp._tool_manager
                for tool in result:
                    if tool.name not in available_tool_names:
                        tool_manager.remove_tool(tool.name)
            except Exception as e:
                print(f"Tool manager sync error: {str(e)}")
        return filtered_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                print(f"Calling tool: {tool.name} with args: {context.message.args}")
            except Exception:
                pass
        return await call_next(context)