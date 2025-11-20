import jwt
from jwt import PyJWKClient
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token, AccessToken

class AuthHelper:
    def __init__(self, tenant_id, client_id, client_secret, audience):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.bearer_auth = JWTVerifier(
                jwks_uri=f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys",
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",  # v2.0 format
                audience=self.audience
            )
        self.jwks_client = PyJWKClient(
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys")

        self.bearer_auth = JWTVerifier(
            jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",  # v2.0 format
            audience=audience
        )

    async def get_token_info(self):
        access_token: AccessToken = get_access_token()
        signing_key = self.jwks_client.get_signing_key_from_jwt(access_token.token)
        token_info = jwt.decode(
            access_token.token, 
            signing_key.key,
            algorithms=["RS256"],
            audience=f"{self.client_id}",
            issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
            options={"verify_signature": True}
        )

        return token_info

    async def is_role_allowed(self, user_roles, required_roles):
        return len(required_roles & user_roles) > 0