import time
from msal import ConfidentialClientApplication
from fastmcp.server.auth.providers.jwt import JWTVerifier

###
# NOT BEING USED CURRENTLY
###
class AuthContext:
    def __init__(self, tenant_id, client_id, client_secret, audience):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = [f"api://{client_id}/access_as_user"]
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        self.msal_app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority
        )

        self.bearer_auth = JWTVerifier(
            jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",  # v2.0 format
            audience=audience
        )

    def get_token_data(self, result: dict) -> dict:
        return {
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "expires_at": time.time() + result.get("expires_in", 3600),
            "id_token_claims": result.get("id_token_claims")
        }