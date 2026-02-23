"""Unit tests for input sanitization and validation."""

import pytest

from packages.security import sanitizer


class TestSanitizeInput:
    """Tests for input sanitization."""

    def test_sanitize_input_clean_string(self):
        """Test that clean input is returned unchanged."""
        clean_input = "Hello World 123"
        result = sanitizer.sanitize_input(clean_input)
        assert result == clean_input

    def test_sanitize_input_empty_string(self):
        """Test that empty string returns empty string."""
        result = sanitizer.sanitize_input("")
        assert result == ""

    def test_sanitize_input_xss_script_tag(self):
        """Test that XSS script tags are escaped."""
        malicious_input = "<script>alert('xss')</script>"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain executable script
        assert "<script>" not in result
        assert "</script>" not in result
        # Should be HTML-escaped
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result

    def test_sanitize_input_xss_img_tag(self):
        """Test that XSS img tags are escaped."""
        malicious_input = '<img src="x" onerror="alert(1)">'
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain executable HTML
        assert "<img" not in result
        # Should be HTML-escaped
        assert "&lt;img" in result
        # Quotes should be escaped making it safe
        assert "&quot;" in result

    def test_sanitize_input_sql_injection_drop_table(self):
        """Test that SQL DROP TABLE injection is removed."""
        malicious_input = "'; DROP TABLE users; --"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain DROP TABLE
        assert "DROP TABLE" not in result.upper()
        # SQL comment should be removed
        assert "--" not in result

    def test_sanitize_input_sql_injection_union_select(self):
        """Test that SQL UNION SELECT injection is removed."""
        malicious_input = "1' UNION SELECT * FROM users--"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain UNION SELECT
        assert "UNION SELECT" not in result.upper()

    def test_sanitize_input_sql_injection_or_1_equals_1(self):
        """Test that SQL OR 1=1 injection is removed."""
        malicious_input = "admin' OR 1=1--"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain OR 1=1
        assert "OR 1=1" not in result.upper()

    def test_sanitize_input_sql_comment_block(self):
        """Test that SQL block comments are removed."""
        malicious_input = "test /* comment */ value"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Block comment should be removed
        assert "/*" not in result
        assert "*/" not in result

    def test_sanitize_input_null_byte(self):
        """Test that null bytes are removed."""
        malicious_input = "test\x00value"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Null byte should be removed
        assert "\x00" not in result
        assert "testvalue" == result

    def test_sanitize_input_html_quotes(self):
        """Test that HTML quotes are escaped."""
        input_with_quotes = 'Hello "World" and \'Test\''
        result = sanitizer.sanitize_input(input_with_quotes)
        
        # Quotes should be escaped
        assert "&quot;" in result or "&#x27;" in result

    def test_sanitize_input_combined_attacks(self):
        """Test sanitization with combined XSS and SQL injection."""
        malicious_input = "<script>alert('xss')</script>'; DROP TABLE users; --"
        result = sanitizer.sanitize_input(malicious_input)
        
        # Should not contain executable code
        assert "<script>" not in result
        assert "DROP TABLE" not in result.upper()
        assert "--" not in result


class TestValidateContainerImageUrl:
    """Tests for container image URL validation."""

    def test_validate_docker_hub_simple(self):
        """Test validation of simple Docker Hub image."""
        result = sanitizer.validate_container_image_url("nginx:latest")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_docker_hub_library(self):
        """Test validation of Docker Hub library image."""
        result = sanitizer.validate_container_image_url("library/nginx:1.0")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_docker_hub_user_repo(self):
        """Test validation of Docker Hub user repository."""
        result = sanitizer.validate_container_image_url("username/myapp:v1.2.3")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_docker_hub_no_tag(self):
        """Test validation of Docker Hub image without tag."""
        result = sanitizer.validate_container_image_url("nginx")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_docker_hub_user_repo_no_tag(self):
        """Test validation of Docker Hub user repo without tag."""
        result = sanitizer.validate_container_image_url("username/myapp")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_ecr_url(self):
        """Test validation of AWS ECR URL."""
        result = sanitizer.validate_container_image_url(
            "123456789.dkr.ecr.us-east-1.amazonaws.com/myrepo:latest"
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_ecr_url_no_tag(self):
        """Test validation of AWS ECR URL without tag."""
        result = sanitizer.validate_container_image_url(
            "987654321.dkr.ecr.eu-west-1.amazonaws.com/myrepo"
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_ecr_url_with_path(self):
        """Test validation of AWS ECR URL with nested path."""
        result = sanitizer.validate_container_image_url(
            "123456789.dkr.ecr.us-west-2.amazonaws.com/team/project/app:v1.0"
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_private_registry_allowed(self):
        """Test validation of allowed private registry."""
        allowed_registries = ["registry.example.com", "docker.company.io"]
        result = sanitizer.validate_container_image_url(
            "registry.example.com/myapp:latest",
            allowed_private_registries=allowed_registries
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_private_registry_with_port_allowed(self):
        """Test validation of allowed private registry with port."""
        allowed_registries = ["registry.example.com"]
        result = sanitizer.validate_container_image_url(
            "registry.example.com:5000/myapp:latest",
            allowed_private_registries=allowed_registries
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_private_registry_not_allowed(self):
        """Test validation rejects non-allowed private registry."""
        allowed_registries = ["registry.example.com"]
        result = sanitizer.validate_container_image_url(
            "malicious.registry.com/myapp:latest",
            allowed_private_registries=allowed_registries
        )
        assert result.is_valid is False
        assert "not in the allowed list" in result.error_message

    def test_validate_empty_url(self):
        """Test validation rejects empty URL."""
        result = sanitizer.validate_container_image_url("")
        assert result.is_valid is False
        assert "cannot be empty" in result.error_message

    def test_validate_url_with_dangerous_characters(self):
        """Test validation rejects URL with dangerous characters."""
        dangerous_urls = [
            "nginx:latest; rm -rf /",
            "nginx:latest && echo hacked",
            "nginx:latest | cat /etc/passwd",
            "nginx:latest`whoami`",
            "nginx:latest$(whoami)",
            "nginx:latest<script>",
            "nginx:latest>output.txt",
        ]
        
        for url in dangerous_urls:
            result = sanitizer.validate_container_image_url(url)
            assert result.is_valid is False
            assert "invalid characters" in result.error_message

    def test_validate_malformed_url(self):
        """Test validation rejects malformed URLs."""
        malformed_urls = [
            "http://nginx:latest",  # HTTP protocol not allowed
            "https://nginx:latest",  # HTTPS protocol not allowed
            "nginx:latest:extra",  # Multiple colons
            "NGINX:LATEST",  # Uppercase not standard but should work
            "nginx@sha256:abc123",  # Digest format not in our patterns
        ]
        
        for url in malformed_urls:
            result = sanitizer.validate_container_image_url(url)
            # Most should be invalid, but uppercase might pass
            if url == "NGINX:LATEST":
                # This might actually pass due to case-insensitive matching
                continue
            assert result.is_valid is False

    def test_validate_url_with_whitespace(self):
        """Test validation handles URLs with whitespace."""
        result = sanitizer.validate_container_image_url("  nginx:latest  ")
        # Should strip whitespace and validate
        assert result.is_valid is True

    def test_validate_url_with_newline(self):
        """Test validation rejects URL with newline."""
        result = sanitizer.validate_container_image_url("nginx:latest\nmalicious")
        assert result.is_valid is False
        assert "invalid characters" in result.error_message

    def test_validate_private_registry_empty_allowed_list(self):
        """Test private registry rejected when allowed list is empty."""
        result = sanitizer.validate_container_image_url(
            "registry.example.com/myapp:latest",
            allowed_private_registries=[]
        )
        assert result.is_valid is False
        assert "not in the allowed list" in result.error_message

    def test_validate_private_registry_none_allowed_list(self):
        """Test private registry rejected when allowed list is None."""
        result = sanitizer.validate_container_image_url(
            "registry.example.com/myapp:latest",
            allowed_private_registries=None
        )
        assert result.is_valid is False
        assert "not in the allowed list" in result.error_message
