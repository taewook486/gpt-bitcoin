"""
Unit tests for logging configuration.

Tests cover:
- setup_logging function
- get_logger function
- mask_sensitive_data_processor
"""

import logging

import pytest

from gpt_bitcoin.infrastructure.logging import (
    get_logger,
    mask_sensitive_data_processor,
    setup_logging,
)


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default(self):
        """setup_logging should work with defaults."""
        # Should not raise
        setup_logging()

    def test_setup_logging_with_level(self):
        """setup_logging should accept log level."""
        setup_logging(log_level="DEBUG")

    def test_setup_logging_with_json_format(self):
        """setup_logging should accept JSON format."""
        setup_logging(log_format="json")


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a logger."""
        logger = get_logger("test_module")

        assert logger is not None

    def test_get_logger_without_name(self):
        """get_logger should work without a name."""
        logger = get_logger()

        assert logger is not None


class TestMaskSensitiveDataProcessor:
    """Test mask_sensitive_data_processor function."""

    def test_mask_api_key(self):
        """Processor should mask api_key field."""
        event_dict = {"api_key": "sk-1234567890abcdef"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        # First 4 chars + asterisks for the rest
        assert result["api_key"].startswith("sk-1")
        assert "*" in result["api_key"]
        assert "234567890abcdef" not in result["api_key"]

    def test_mask_access_key(self):
        """Processor should mask access_key field."""
        event_dict = {"access_key": "access123456"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["access_key"].startswith("acce")
        assert "*" in result["access_key"]
        assert "ss123456" not in result["access_key"]

    def test_mask_secret_key(self):
        """Processor should mask secret_key field."""
        event_dict = {"secret_key": "secret789012"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["secret_key"].startswith("secr")
        assert "*" in result["secret_key"]
        assert "et789012" not in result["secret_key"]

    def test_mask_short_values(self):
        """Processor should mask short values completely."""
        event_dict = {"api_key": "abc"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["api_key"] == "****"

    def test_preserve_non_sensitive_data(self):
        """Processor should preserve non-sensitive fields."""
        event_dict = {
            "message": "Test message",
            "count": 42,
            "data": {"nested": "value"},
        }
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["message"] == "Test message"
        assert result["count"] == 42
        assert result["data"] == {"nested": "value"}

    def test_mask_password(self):
        """Processor should mask password field."""
        event_dict = {"password": "mypassword123"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["password"].startswith("mypa")
        assert "*" in result["password"]
        assert "ssword123" not in result["password"]

    def test_mask_token(self):
        """Processor should mask token field."""
        event_dict = {"token": "bearer_token_xyz"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["token"].startswith("bear")
        assert "*" in result["token"]
        assert "er_token_xyz" not in result["token"]

    def test_mask_authorization(self):
        """Processor should mask authorization field."""
        event_dict = {"authorization": "Bearer xyz123"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["authorization"].startswith("Bear")
        assert "*" in result["authorization"]
        assert "er xyz123" not in result["authorization"]

    def test_mask_credential(self):
        """Processor should mask credential field."""
        event_dict = {"credential": "cred_abc123"}
        result = mask_sensitive_data_processor(None, None, event_dict)

        assert result["credential"].startswith("cred")
        assert "*" in result["credential"]
        assert "_abc123" not in result["credential"]
