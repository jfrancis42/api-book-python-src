class GitHubError(Exception):
    """Base class for GitHub API errors."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class NotFoundError(GitHubError):
    """The requested resource does not exist."""


class AuthenticationError(GitHubError):
    """The request was not authenticated or the token is invalid."""


class PermissionError(GitHubError):
    """The authenticated user does not have permission for this operation."""


class RateLimitError(GitHubError):
    """The API rate limit has been exceeded."""
    def __init__(self, message, reset_at=None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_at = reset_at


class ServerError(GitHubError):
    """The GitHub API returned a 5xx response."""


class ValidationError(GitHubError):
    """The request was rejected due to invalid input (422)."""
