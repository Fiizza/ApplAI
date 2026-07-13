"""
Gmail OAuth flow (read-only access) + credential refresh helpers.

Setup required in Google Cloud Console (console.cloud.google.com):
  1. Create a project (or use an existing one).
  2. Enable the "Gmail API" under APIs & Services -> Library.
  3. APIs & Services -> OAuth consent screen: add the "gmail.readonly" scope,
     and while your app is in "Testing" mode, add your own Google account as a test user
     (otherwise Google blocks the consent screen for anyone but you).
  4. APIs & Services -> Credentials -> Create Credentials -> OAuth client ID -> Web application.
     Add an "Authorized redirect URI" that matches GOOGLE_REDIRECT_URI below exactly.

Required environment variables:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI   e.g. http://localhost:8000/auth/gmail/callback
"""
import os
import secrets
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from jose import jwt

from .auth import SECRET_KEY, ALGORITHM  # reuse the same JWT secret already configured

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback")

# Read-only on purpose — this app never sends, deletes, or modifies email.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def build_auth_url(user_id: int) -> str:
    """The OAuth redirect is a full browser navigation, not a fetch call, so it can't carry
    your Bearer token. Instead we encode the user id into a short-lived signed 'state' param
    and verify it when Google redirects back to /auth/gmail/callback.

    We also generate a PKCE code_verifier here and carry it inside that same signed state —
    Google now requires PKCE even for confidential 'Web application' clients, and the
    verifier has to survive the round trip through Google's consent screen and back."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set in .env")

    code_verifier = secrets.token_urlsafe(64)[:128]  # PKCE spec: 43-128 chars

    state = jwt.encode(
        {"uid": user_id, "cv": code_verifier, "exp": datetime.utcnow() + timedelta(minutes=10)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI, code_verifier=code_verifier
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",     # required to receive a refresh_token
        prompt="consent",          # forces a refresh_token on every connect, not just the first ever
        include_granted_scopes="true",
        state=state,
    )
    return auth_url


def verify_state(state: str) -> tuple[int, str]:
    """Returns (user_id, code_verifier) encoded in the state param, or raises if invalid/expired."""
    payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["uid"]), payload.get("cv")


def exchange_code_for_tokens(code: str, code_verifier: str = None) -> dict:
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI, code_verifier=code_verifier
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": creds.expiry,
    }


def credentials_from_tokens(access_token: str, refresh_token: str) -> Credentials:
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def get_valid_credentials(account) -> Credentials:
    """Rebuilds a Credentials object from stored tokens, refreshing if expired.
    Caller is responsible for persisting the refreshed access_token/expiry back to the DB
    (sync_gmail_for_user in gmail_sync.py does this)."""
    creds = credentials_from_tokens(account.access_token, account.refresh_token)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
    return creds