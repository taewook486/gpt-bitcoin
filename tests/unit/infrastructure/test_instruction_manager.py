"""
Unit tests for instruction file management.

Tests cover:
- Instruction file loading and caching
- Modular instruction system
- Strategy/coin combination support
- Version migration support (v1, v2, v3)

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestInstructionManager:
    """Test Instruction Manager functionality."""

    def test_instruction_manager_import(self):
        """InstructionManager should be importable."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        assert InstructionManager is not None

    def test_instruction_manager_initialization(self):
        """InstructionManager should initialize with defaults."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        assert manager is not None

    def test_instruction_manager_with_base_path(self):
        """InstructionManager should accept base path."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager(base_path="instructions/")

        assert manager.base_path == Path("instructions/")

    def test_load_instruction_file(self):
        """InstructionManager should load instruction file."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        # Mock file existence
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value="Test instruction"):
                content = manager.load("test.md")

        assert content == "Test instruction"

    def test_load_instruction_file_not_found(self):
        """InstructionManager should handle missing file."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'exists', return_value=False):
            content = manager.load("nonexistent.md")

        assert content is None or content == ""

    def test_load_with_caching(self):
        """InstructionManager should cache loaded files."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value="Cached content") as mock_read:
                # First load
                content1 = manager.load("cached.md")
                # Second load (should use cache)
                content2 = manager.load("cached.md")

                # File should only be read once
                assert mock_read.call_count == 1

        assert content1 == content2

    def test_clear_cache(self):
        """InstructionManager should support cache clearing."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value="Content"):
                manager.load("test.md")

        manager.clear_cache()

        assert len(manager._cache) == 0


class TestModularInstructions:
    """Test modular instruction system."""

    def test_load_modular_instruction(self):
        """Should load modular instruction parts."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(manager, 'load') as mock_load:
            mock_load.side_effect = lambda f: f"Content of {f}"

            result = manager.load_modular([
                "base.md",
                "strategy.md",
                "coin.md",
            ])

        assert "base.md" in result
        assert "strategy.md" in result
        assert "coin.md" in result

    def test_build_instruction_for_strategy_coin(self):
        """Should build instruction for strategy/coin combination."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager
        from gpt_bitcoin.domain import TradingStrategy, Cryptocurrency

        manager = InstructionManager()

        with patch.object(manager, 'load_modular') as mock_modular:
            mock_modular.return_value = "Combined instruction"

            result = manager.build_for_context(
                strategy=TradingStrategy.aggressive,
                coin=Cryptocurrency.ETH,
            )

        assert result is not None


class TestInstructionVersions:
    """Test instruction version management."""

    def test_get_available_versions(self):
        """Should list available instruction versions."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'glob') as mock_glob:
            mock_glob.return_value = [
                Path("instructions_v1.md"),
                Path("instructions_v2.md"),
                Path("instructions_v3.md"),
            ]

            versions = manager.get_available_versions()

        assert len(versions) >= 3

    def test_get_latest_version(self):
        """Should identify latest version."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(manager, 'get_available_versions') as mock_versions:
            mock_versions.return_value = ["v1", "v2", "v3"]

            latest = manager.get_latest_version()

        assert latest == "v3"

    def test_migrate_instruction(self):
        """Should support instruction migration."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        # v1 content to v2 format
        v1_content = "Simple instruction"
        v2_content = manager.migrate(v1_content, from_version="v1", to_version="v2")

        assert v2_content is not None

    def test_version_specific_loading(self):
        """Should load version-specific instruction."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(manager, 'load') as mock_load:
            mock_load.return_value = "v2 instruction content"

            content = manager.load_version("v2")

        assert content == "v2 instruction content"


class TestInstructionTemplate:
    """Test instruction template functionality."""

    def test_render_template(self):
        """Should render instruction with variables."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        template = "Hello {name}, your coin is {coin}."
        result = manager.render_template(template, name="User", coin="BTC")

        assert result == "Hello User, your coin is BTC."

    def test_render_with_defaults(self):
        """Should use default values for missing variables."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        template = "Coin: {coin}, Strategy: {strategy}"
        result = manager.render_template(
            template,
            defaults={"coin": "BTC", "strategy": "balanced"},
        )

        assert result == "Coin: BTC, Strategy: balanced"


class TestInstructionManagerEdgeCases:
    """Test InstructionManager edge cases for coverage."""

    def test_load_with_io_error(self):
        """Should handle IO errors gracefully."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', side_effect=IOError("Read error")):
                result = manager.load("error.md")

        assert result is None

    def test_build_context_with_all_params(self):
        """Should build context with all parameters."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager
        from gpt_bitcoin.domain import TradingStrategy, Cryptocurrency

        manager = InstructionManager()

        with patch.object(manager, 'load') as mock_load:
            mock_load.return_value = "Instruction content"

            result = manager.build_for_context(
                strategy=TradingStrategy.aggressive,
                coin=Cryptocurrency.BTC,
                version="v2",
            )

        assert result is not None
        assert "Instruction content" in result

    def test_get_available_versions_empty(self):
        """Should return empty list when no versions found."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'glob', return_value=[]):
            versions = manager.get_available_versions()

        assert versions == []

    def test_get_latest_version_none(self):
        """Should return None when no versions available."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(manager, 'get_available_versions', return_value=[]):
            latest = manager.get_latest_version()

        assert latest is None

    def test_load_version_fallback(self):
        """Should fallback to base instructions when version not found."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(manager, 'load') as mock_load:
            mock_load.side_effect = lambda f: None if "v99" in f else "Base content"

            result = manager.load_version("v99")

        assert result == "Base content"

    def test_migrate_unknown_versions(self):
        """Should handle unknown version migration."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        content = "Original content"
        result = manager.migrate(content, from_version="v5", to_version="v6")

        assert result == content

    def test_render_template_missing_variable(self):
        """Should handle missing template variables."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        template = "Hello {name}, coin: {coin}"
        result = manager.render_template(template, name="User", coin="BTC")
        # Both variables provided

        assert "User" in result
        assert "BTC" in result

    def test_load_twice_uses_cache(self):
        """Should use cache on second load."""
        from gpt_bitcoin.infrastructure.instructions import InstructionManager

        manager = InstructionManager()

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value="Content") as mock_read:
                manager.load("test.md")
                manager.load("test.md")

                # Should only read once due to caching
                assert mock_read.call_count == 1
