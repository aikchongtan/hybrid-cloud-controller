"""Input sanitization and validation for security."""

import html
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of validation with success status and optional error message."""

    is_valid: bool
    error_message: Optional[str] = None


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent SQL injection and XSS attacks.

    This function:
    - Escapes HTML special characters to prevent XSS
    - Removes SQL injection patterns
    - Removes dangerous characters that could be used in attacks

    Args:
        input_str: The user input string to sanitize

    Returns:
        Sanitized string safe for use in HTML and database queries

    Note:
        This is a defense-in-depth measure. Always use parameterized queries
        for SQL and proper template escaping for HTML rendering.
    """
    if not input_str:
        return ""

    # First, escape HTML special characters to prevent XSS
    sanitized = html.escape(input_str, quote=True)

    # Remove common SQL injection patterns
    # Note: This is additional protection - parameterized queries are the primary defense
    sql_patterns = [
        r";\s*DROP\s+TABLE",
        r";\s*DELETE\s+FROM",
        r";\s*UPDATE\s+.*\s+SET",
        r";\s*INSERT\s+INTO",
        r";\s*CREATE\s+TABLE",
        r";\s*ALTER\s+TABLE",
        r"--",  # SQL comment
        r"/\*.*?\*/",  # SQL block comment
        r"UNION\s+SELECT",
        r"OR\s+1\s*=\s*1",
        r"OR\s+'1'\s*=\s*'1'",
        r"OR\s+\"1\"\s*=\s*\"1\"",
    ]

    for pattern in sql_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    return sanitized


def validate_container_image_url(url: str, allowed_private_registries: Optional[list[str]] = None) -> ValidationResult:
    """
    Validate container image URL format and allowed registry domains.

    Supports:
    - Docker Hub: nginx:latest, library/nginx:1.0, username/repo:tag
    - ECR: 123456789.dkr.ecr.us-east-1.amazonaws.com/repo:tag
    - Private registries: registry.example.com/repo:tag (if in allowed list)

    Args:
        url: Container image URL to validate
        allowed_private_registries: Optional list of allowed private registry domains

    Returns:
        ValidationResult with is_valid=True if URL is valid, False otherwise
    """
    if not url:
        return ValidationResult(is_valid=False, error_message="Container image URL cannot be empty")

    if allowed_private_registries is None:
        allowed_private_registries = []

    # Remove whitespace
    url = url.strip()

    # Check for dangerous characters
    if any(char in url for char in [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]):
        return ValidationResult(
            is_valid=False,
            error_message="Container image URL contains invalid characters"
        )

    # Pattern 1: Docker Hub format
    # Examples: nginx:latest, library/nginx:1.0, username/repo:tag, username/repo
    docker_hub_pattern = r"^([a-z0-9_-]+/)?[a-z0-9_-]+(:[a-zA-Z0-9._-]+)?$"

    # Pattern 2: ECR format
    # Example: 123456789.dkr.ecr.us-east-1.amazonaws.com/repo:tag
    ecr_pattern = r"^\d+\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9/_-]+(:[a-zA-Z0-9._-]+)?$"

    # Pattern 3: Private registry format
    # Example: registry.example.com/repo:tag, registry.example.com:5000/repo:tag
    private_registry_pattern = r"^([a-z0-9.-]+)(:\d+)?/[a-z0-9/_-]+(:[a-zA-Z0-9._-]+)?$"

    # Check Docker Hub format
    if re.match(docker_hub_pattern, url, re.IGNORECASE):
        return ValidationResult(is_valid=True)

    # Check ECR format
    if re.match(ecr_pattern, url, re.IGNORECASE):
        return ValidationResult(is_valid=True)

    # Check private registry format
    private_match = re.match(private_registry_pattern, url, re.IGNORECASE)
    if private_match:
        # Extract registry domain (everything before the first /)
        registry_domain = url.split("/")[0]
        # Remove port if present
        registry_host = registry_domain.split(":")[0]

        # Check if registry is in allowed list
        if registry_host in allowed_private_registries:
            return ValidationResult(is_valid=True)
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Private registry '{registry_host}' is not in the allowed list"
            )

    # If no pattern matched, URL is invalid
    return ValidationResult(
        is_valid=False,
        error_message="Container image URL format is invalid. "
        "Supported formats: Docker Hub (nginx:latest), "
        "ECR (123456789.dkr.ecr.region.amazonaws.com/repo:tag), "
        "or allowed private registries"
    )
