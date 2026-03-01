"""HTTPS enforcement middleware for API security."""

import logging

from flask import current_app, request
from werkzeug.exceptions import Forbidden

logger = logging.getLogger("hybrid_cloud.api.middleware.https")


def enforce_https() -> None:
    """
    Enforce HTTPS for all API requests.

    Validates: Requirements 12.10, 12.11

    Raises:
        Forbidden: If request is not over HTTPS when HTTPS is required
    """
    # Skip HTTPS check if disabled in config (for development)
    if not current_app.config.get("REQUIRE_HTTPS", True):
        return

    # Check if request is secure
    if not request.is_secure:
        logger.warning(
            f"Rejected non-HTTPS request: {request.method} {request.path}",
            extra={"remote_addr": request.remote_addr},
        )
        raise Forbidden("HTTPS is required for all API requests")

    logger.debug(f"HTTPS check passed for {request.method} {request.path}")
