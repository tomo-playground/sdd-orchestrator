"""YouTube service exceptions."""


class YouTubeError(Exception):
    """Base YouTube error."""


class YouTubeAuthError(YouTubeError):
    """OAuth authentication failure."""


class YouTubeUploadError(YouTubeError):
    """Video upload failure."""


class YouTubeQuotaError(YouTubeError):
    """API quota exceeded."""
