"""
Unit tests for dependency injection container.

Tests cover:
- Container initialization
- Provider resolution
- Override functionality for testing
- Container lifecycle management
"""

from gpt_bitcoin.dependencies.container import (
    clear_overrides,
    get_container,
    reset_container,
)


class TestContainer:
    """Test Container class."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Clean up after each test."""
        reset_container()

    def test_get_container_returns_singleton(self):
        """get_container should return the same instance."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_container_has_settings_provider(self):
        """Container should have settings provider."""
        container = get_container()

        assert hasattr(container, "settings")
        assert container.settings is not None

    def test_container_has_glm_client_provider(self):
        """Container should have GLM client provider."""
        container = get_container()

        assert hasattr(container, "glm_client")
        assert container.glm_client is not None

    def test_container_has_upbit_client_provider(self):
        """Container should have Upbit client provider."""
        container = get_container()

        assert hasattr(container, "upbit_client")
        assert container.upbit_client is not None

    def test_reset_container_clears_instance(self):
        """reset_container should clear the singleton instance."""
        container1 = get_container()
        reset_container()
        container2 = get_container()

        # Different instances after reset
        assert container1 is not container2


class TestClearOverrides:
    """Test clear_overrides function."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Clean up after each test."""
        reset_container()

    def test_clear_overrides_does_not_error(self):
        """clear_overrides should not raise errors."""
        container = get_container()

        # Should not raise even without overrides
        clear_overrides()

        # Container should still work
        assert container is not None


class TestContainerLifecycle:
    """Test container lifecycle management."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Clean up after each test."""
        reset_container()

    def test_multiple_resets(self):
        """Multiple resets should not cause errors."""
        get_container()
        reset_container()
        reset_container()
        reset_container()

        # Should still work after multiple resets
        container = get_container()
        assert container is not None

    def test_get_container_after_reset(self):
        """get_container should work after reset."""
        container1 = get_container()
        reset_container()
        container2 = get_container()

        assert container1 is not container2
        assert hasattr(container2, "settings")
        assert hasattr(container2, "glm_client")
        assert hasattr(container2, "upbit_client")


class TestOverrideForTesting:
    """Test override_for_testing function - covers lines 142-150."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Clean up after each test."""
        reset_container()

    def test_override_glm_client(self):
        """override_for_testing should override GLM client."""
        from unittest.mock import MagicMock

        from gpt_bitcoin.dependencies.container import override_for_testing

        mock_glm = MagicMock()
        container = override_for_testing(glm_client=mock_glm)

        # The overridden client should be returned
        assert container.glm_client() is mock_glm

    def test_override_upbit_client(self):
        """override_for_testing should override Upbit client."""
        from unittest.mock import MagicMock

        from gpt_bitcoin.dependencies.container import override_for_testing

        mock_upbit = MagicMock()
        container = override_for_testing(upbit_client=mock_upbit)

        # The overridden client should be returned
        assert container.upbit_client() is mock_upbit

    def test_override_both_clients(self):
        """override_for_testing should override both clients."""
        from unittest.mock import MagicMock

        from gpt_bitcoin.dependencies.container import override_for_testing

        mock_glm = MagicMock()
        mock_upbit = MagicMock()
        container = override_for_testing(
            glm_client=mock_glm,
            upbit_client=mock_upbit,
        )

        assert container.glm_client() is mock_glm
        assert container.upbit_client() is mock_upbit

    def test_override_none_no_change(self):
        """override_for_testing with None should not change anything."""
        from gpt_bitcoin.dependencies.container import override_for_testing

        container = override_for_testing()

        # Container should still be functional
        assert container is not None
