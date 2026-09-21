from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


async def get_current_user(x_api_key: str = Header(...), x_user_id: str = Header(default="unknown")) -> str:
    """Minimal API-key gate for local/dev use.

    Production replacement: OAuth2/OIDC bearer tokens validated against the corporate IdP
    (Okta/Azure AD), with role claims (store-manager, category-manager, admin) enforced via
    FastAPI dependencies per route. See docs/ARCHITECTURE.md - Design Decisions.
    """
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return x_user_id
