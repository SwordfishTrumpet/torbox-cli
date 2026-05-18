"""Custom exception hierarchy for TorBox API errors."""

from __future__ import annotations


class TorBoxError(Exception):
    """Base exception for all TorBox CLI errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class AuthenticationError(TorBoxError):
    """Raised for authentication failures (NO_AUTH, BAD_TOKEN, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=2)


class ValidationError(TorBoxError):
    """Raised for invalid input or options (INVALID_OPTION, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


class NotFoundError(TorBoxError):
    """Raised when an item or endpoint is not found."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=6)


class PlanRestrictedError(TorBoxError):
    """Raised for plan-restricted features (PLAN_RESTRICTED_FEATURE, MONTHLY_LIMIT)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=5)


class DownloadError(TorBoxError):
    """Raised for download-related errors (COOLDOWN_LIMIT, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=3)


class ServerError(TorBoxError):
    """Raised for server-side errors (DATABASE_ERROR, UNKNOWN_ERROR, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=3)


class RateLimitError(TorBoxError):
    """Raised when rate limited (429)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=4)


class ClientError(TorBoxError):
    """Catch-all for client-caused errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


def map_error_code(error_code: str, detail: str) -> TorBoxError:
    """Map TorBox error code to specific exception per Appendix A."""
    mapping: dict[str, type[TorBoxError]] = {
        "DATABASE_ERROR": ServerError,
        "UNKNOWN_ERROR": ServerError,
        "NO_AUTH": AuthenticationError,
        "BAD_TOKEN": AuthenticationError,
        "AUTH_ERROR": AuthenticationError,
        "INVALID_OPTION": ValidationError,
        "REDIRECT_ERROR": ServerError,
        "OAUTH_VERIFICATION_ERROR": AuthenticationError,
        "ENDPOINT_NOT_FOUND": NotFoundError,
        "ITEM_NOT_FOUND": NotFoundError,
        "PLAN_RESTRICTED_FEATURE": PlanRestrictedError,
        "DUPLICATE_ITEM": ValidationError,
        "BOZO_RSS_FEED": ValidationError,
        "TOO_MUCH_DATA": ValidationError,
        "DOWNLOAD_TOO_LARGE": ValidationError,
        "MISSING_REQUIRED_OPTION": ValidationError,
        "TOO_MANY_OPTIONS": ValidationError,
        "BOZO_TORRENT": ValidationError,
        "NO_SERVERS_AVAILABLE_ERROR": ServerError,
        "MONTHLY_LIMIT": PlanRestrictedError,
        "COOLDOWN_LIMIT": DownloadError,
        "ACTIVE_LIMIT": DownloadError,
        "DOWNLOAD_SERVER_ERROR": DownloadError,
        "BOZO_NZB": ValidationError,
        "SEARCH_ERROR": ServerError,
        "INVALID_DEVICE": AuthenticationError,
        "DIFF_ISSUE": ValidationError,
        "LINK_OFFLINE": ValidationError,
        "VENDOR_DISABLED": ValidationError,
        "BOZO_REGEX": ValidationError,
        "BAD_CONFIRMATION": ValidationError,
        "CONFIRMATION_EXPIRED": ValidationError,
        "BOZO_FILE": ValidationError,
        "UNSUPPORTED_SITE": ServerError,
    }
    exc_class = mapping.get(error_code, ServerError)
    return exc_class(detail or error_code)


def map_http_status(status_code: int, detail: str = "") -> TorBoxError:
    """Map HTTP status codes to typed exceptions."""
    if status_code == 429:
        return RateLimitError(detail or "Rate limited. Please retry after a while.")
    if status_code == 403:
        return AuthenticationError(detail or "Authentication failed.")
    if status_code == 404:
        return NotFoundError(detail or "Not found.")
    if status_code == 400:
        return ValidationError(detail or "Bad request.")
    if status_code >= 500:
        return ServerError(detail or "Server error.")
    return ClientError(detail or f"HTTP {status_code}")
