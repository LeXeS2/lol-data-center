"""Response validation and error storage."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from lol_data_center.config import get_settings
from lol_data_center.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class ValidationError(Exception):
    """Exception raised when API response validation fails."""

    def __init__(
        self,
        message: str,
        endpoint: str,
        url: str,
        response_body: str,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.endpoint = endpoint
        self.url = url
        self.response_body = response_body
        self.original_error = original_error


async def validate_response(
    schema: type[T],
    data: Any,
    endpoint: str,
    url: str,
    status_code: int | None = None,
) -> T:
    """Validate API response data against a Pydantic schema.

    If validation fails, the invalid response is stored for debugging.

    Args:
        schema: Pydantic model class to validate against
        data: Raw response data (dict or list)
        endpoint: API endpoint name for logging
        url: Full URL for logging
        status_code: HTTP status code if available

    Returns:
        Validated Pydantic model instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return schema.model_validate(data)
    except PydanticValidationError as e:
        error_msg = f"Validation failed for {endpoint}: {e}"
        logger.error(
            "API response validation failed",
            endpoint=endpoint,
            url=url,
            error=str(e),
            validation_errors=e.errors(),
        )

        # Store invalid response for debugging
        await store_invalid_response(
            endpoint=endpoint,
            url=url,
            status_code=status_code,
            response_body=data,
            error_message=str(e),
        )

        raise ValidationError(
            message=error_msg,
            endpoint=endpoint,
            url=url,
            response_body=json.dumps(data) if not isinstance(data, str) else data,
            original_error=e,
        ) from e


async def store_invalid_response(
    endpoint: str,
    url: str,
    status_code: int | None,
    response_body: Any,
    error_message: str,
) -> Path:
    """Store an invalid API response to a file for debugging.

    Args:
        endpoint: API endpoint name
        url: Full URL
        status_code: HTTP status code
        response_body: Raw response body
        error_message: Validation error message

    Returns:
        Path to the stored file
    """
    settings = get_settings()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    safe_endpoint = endpoint.replace("/", "_").replace(":", "_")
    filename = f"{timestamp}_{safe_endpoint}.json"
    filepath = settings.invalid_responses_dir / filename

    error_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "url": url,
        "status_code": status_code,
        "error_message": error_message,
        "response_body": response_body,
    }

    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            "Stored invalid API response",
            filepath=str(filepath),
            endpoint=endpoint,
        )
        return filepath
    except Exception as e:
        logger.error(
            "Failed to store invalid API response",
            error=str(e),
            endpoint=endpoint,
        )
        raise
