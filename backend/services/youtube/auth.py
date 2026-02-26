"""YouTube OAuth2 authentication and token management."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets

from cryptography.fernet import Fernet, InvalidToken
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from config import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REDIRECT_URI,
    YOUTUBE_SCOPES,
    YOUTUBE_TOKEN_ENCRYPTION_KEY,
)
from models.youtube_credential import YouTubeCredential
from services.youtube.exceptions import YouTubeAuthError

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet cipher from configured encryption key."""
    if not YOUTUBE_TOKEN_ENCRYPTION_KEY:
        raise YouTubeAuthError("YOUTUBE_TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(YOUTUBE_TOKEN_ENCRYPTION_KEY.encode())


def _build_flow() -> Flow:
    """Build Google OAuth2 flow from config."""
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        raise YouTubeAuthError("YouTube OAuth credentials not configured")

    client_config = {
        "web": {
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=YOUTUBE_SCOPES)
    flow.redirect_uri = YOUTUBE_REDIRECT_URI
    return flow


def encrypt_token(data: dict) -> str:
    """Encrypt token data with Fernet."""
    f = _get_fernet()
    return f.encrypt(json.dumps(data).encode()).decode()


def decrypt_token(encrypted: str) -> dict:
    """Decrypt token data with Fernet."""
    f = _get_fernet()
    try:
        return json.loads(f.decrypt(encrypted.encode()).decode())
    except InvalidToken as e:
        raise YouTubeAuthError("Failed to decrypt token — key may have changed") from e


def _sign_state(project_id: int, nonce: str) -> str:
    """Create HMAC-signed OAuth state: project_id.nonce.signature.

    Uses YOUTUBE_TOKEN_ENCRYPTION_KEY as HMAC key for CSRF prevention.
    """
    if not YOUTUBE_TOKEN_ENCRYPTION_KEY:
        raise YouTubeAuthError("YOUTUBE_TOKEN_ENCRYPTION_KEY is not configured")
    payload = f"{project_id}.{nonce}"
    sig = hmac.new(
        YOUTUBE_TOKEN_ENCRYPTION_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{payload}.{sig}"


def verify_oauth_state(state: str) -> int:
    """Verify HMAC-signed OAuth state and return project_id.

    Raises:
        YouTubeAuthError: If signature is invalid or state is malformed.
    """
    if not YOUTUBE_TOKEN_ENCRYPTION_KEY:
        raise YouTubeAuthError("YOUTUBE_TOKEN_ENCRYPTION_KEY is not configured")

    parts = state.split(".")
    if len(parts) != 3:
        raise YouTubeAuthError("Invalid OAuth state format")

    raw_project_id, nonce, received_sig = parts
    payload = f"{raw_project_id}.{nonce}"
    expected_sig = hmac.new(
        YOUTUBE_TOKEN_ENCRYPTION_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]

    if not hmac.compare_digest(received_sig, expected_sig):
        raise YouTubeAuthError("Invalid OAuth state signature (possible CSRF)")

    try:
        return int(raw_project_id)
    except ValueError as e:
        raise YouTubeAuthError("Invalid project_id in OAuth state") from e


def generate_auth_url(project_id: int) -> str:
    """Generate Google OAuth URL with HMAC-signed state for CSRF prevention."""
    flow = _build_flow()
    nonce = secrets.token_hex(16)
    signed_state = _sign_state(project_id, nonce)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=signed_state,
    )
    return auth_url


def exchange_code(code: str, project_id: int, db: Session) -> YouTubeCredential:
    """Exchange authorization code for tokens, encrypt and store.

    Upserts the credential for the given project (1:1).
    """
    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Build token payload for encryption
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or []),
    }
    if credentials.expiry:
        token_data["expiry"] = credentials.expiry.isoformat()

    encrypted = encrypt_token(token_data)

    # Fetch channel info
    youtube = build("youtube", "v3", credentials=credentials)
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    channel_id = items[0]["id"] if items else None
    channel_title = items[0]["snippet"]["title"] if items else None

    # Upsert: update existing or create new
    cred = db.query(YouTubeCredential).filter(YouTubeCredential.project_id == project_id).first()
    if cred:
        cred.encrypted_token = encrypted
        cred.channel_id = channel_id
        cred.channel_title = channel_title
        cred.is_valid = True
    else:
        cred = YouTubeCredential(
            project_id=project_id,
            encrypted_token=encrypted,
            channel_id=channel_id,
            channel_title=channel_title,
            is_valid=True,
        )
        db.add(cred)

    db.commit()
    db.refresh(cred)
    logger.info("YouTube credential saved for project %d (channel: %s)", project_id, channel_title)
    return cred


def get_authenticated_service(db: Session, project_id: int):
    """Get authenticated YouTube API client, refreshing token if needed."""
    cred = (
        db.query(YouTubeCredential)
        .filter(
            YouTubeCredential.project_id == project_id,
            YouTubeCredential.is_valid.is_(True),
        )
        .first()
    )
    if not cred:
        raise YouTubeAuthError(f"No valid YouTube credential for project {project_id}")

    token_data = decrypt_token(cred.encrypted_token)
    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", YOUTUBE_CLIENT_ID),
        client_secret=token_data.get("client_secret", YOUTUBE_CLIENT_SECRET),
        scopes=token_data.get("scopes"),
    )

    return build("youtube", "v3", credentials=credentials)


def revoke_credential(db: Session, project_id: int) -> None:
    """Revoke YouTube credential for a project."""
    cred = db.query(YouTubeCredential).filter(YouTubeCredential.project_id == project_id).first()
    if not cred:
        return
    cred.is_valid = False
    db.commit()
    logger.info("YouTube credential revoked for project %d (channel: %s)", project_id, cred.channel_title)
