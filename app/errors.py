"""Domain errors. Services raise these; main.py turns them into clean JSON."""


class AppError(Exception):
    status_code = 400
    message = "Bad request"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class NotFoundError(AppError):
    status_code = 404
    message = "Not found"


class UnauthorizedError(AppError):
    status_code = 401
    message = "Unauthorized"


class AuthUnavailableError(AppError):
    status_code = 503
    message = "Auth service unavailable"


class FieldValidationError(AppError):
    """Submitted data does not match the widget's field definitions."""

    status_code = 422
    message = "Submission does not match the widget's fields"

    def __init__(self, errors: list[dict]):
        super().__init__()
        self.errors = errors
