from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
import os
import secrets

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# The API key is sourced from the API_KEY environment variable.
# It should be a strong, secret value injected by the deployment environment.
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header and secrets.compare_digest(api_key_header, API_KEY):
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")
