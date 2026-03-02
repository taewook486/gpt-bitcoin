"""
Unit tests for dependencies module.

Tests cover:
- Container class
- get_container function
"""

import pytest

from gpt_bitcoin.dependencies import get_container
from gpt_bitcoin.dependencies.container import reset_container


class TestContainerImport:
    """Test Container import."""

    def test_container_module_exists(self):
        """Container module should exist."""
        from gpt_bitcoin.dependencies import container

        assert container is not None

    def test_get_container_is_callable(self):
        """get_container should be callable."""
        assert callable(get_container)


class TestContainerInstance:
    """Test Container instance."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Clean up after each test."""
        reset_container()

    def test_get_container_returns_object(self):
        """get_container should return an object with expected attributes."""
        reset_container()
        container = get_container()

        assert container is not None
        assert hasattr(container, "settings")
        assert hasattr(container, "glm_client")
        assert hasattr(container, "upbit_client")

    def test_container_has_providers(self):
        """Container should have expected providers."""
        reset_container()
        container = get_container()

        assert container.settings is not None
        assert container.glm_client is not None
        assert container.upbit_client is not None

    def test_get_container_caches_instance(self):
        """get_container should return cached instance."""
        reset_container()
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_reset_container_clears_instance(self):
        """reset_container should clear the instance."""
        container1 = get_container()
        reset_container()
        container2 = get_container()

        # Different instances after reset
        assert container1 is not container2
