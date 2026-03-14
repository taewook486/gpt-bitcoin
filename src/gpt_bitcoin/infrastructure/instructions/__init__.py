"""
Instruction file management module.

This module provides:
- Instruction file loading and caching
- Modular instruction system
- Strategy/coin combination support
- Version migration support (v1, v2, v3)

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 8.5 instruction file management.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gpt_bitcoin.infrastructure.logging import get_logger


class InstructionManager:
    """
    Manage instruction files with caching and version support.

    Provides functionality for:
    - Loading instruction files with caching
    - Building modular instructions
    - Strategy/coin specific instructions
    - Version management and migration

    Example:
        ```python
        manager = InstructionManager(base_path="instructions/")

        # Load simple instruction
        content = manager.load("instructions.md")

        # Build for specific context
        instruction = manager.build_for_context(
            strategy=TradingStrategy.aggressive,
            coin=Cryptocurrency.ETH,
        )
        ```
    """

    def __init__(self, base_path: str | Path = "."):
        """
        Initialize InstructionManager.

        Args:
            base_path: Base directory for instruction files
        """
        self._base_path = Path(base_path)
        self._cache: dict[str, str] = {}
        self._logger = get_logger("instruction_manager")

    @property
    def base_path(self) -> Path:
        """Get base path for instruction files."""
        return self._base_path

    @property
    def _cache_internal(self) -> dict[str, str]:
        """Access to internal cache for testing."""
        return self._cache

    def load(self, filename: str) -> str | None:
        """
        Load instruction file with caching.

        Args:
            filename: Instruction file name

        Returns:
            File content or None if not found
        """
        # Check cache first
        if filename in self._cache:
            return self._cache[filename]

        file_path = self._base_path / filename

        if not file_path.exists():
            self._logger.warning("Instruction file not found", filename=filename)
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            self._cache[filename] = content
            return content
        except Exception as e:
            self._logger.error("Failed to load instruction file", filename=filename, error=str(e))
            return None

    def clear_cache(self) -> None:
        """Clear the instruction cache."""
        self._cache.clear()
        self._logger.info("Instruction cache cleared")

    def load_modular(self, parts: list[str]) -> str:
        """
        Load and combine multiple instruction files.

        Args:
            parts: List of instruction file names to combine

        Returns:
            Combined instruction content
        """
        combined = []

        for part in parts:
            content = self.load(part)
            if content:
                combined.append(f"=== {part} ===\n{content}")

        return "\n\n".join(combined)

    def build_for_context(
        self,
        strategy: Any = None,
        coin: Any = None,
        version: str | None = None,
    ) -> str:
        """
        Build instruction for specific strategy/coin context.

        Args:
            strategy: Trading strategy enum
            coin: Cryptocurrency enum
            version: Instruction version (v1, v2, v3)

        Returns:
            Combined instruction for the context
        """
        parts = []

        # Base instruction
        base_file = "instructions.md"
        if version:
            base_file = f"instructions_{version}.md"
        parts.append(base_file)

        # Strategy-specific instruction
        if strategy:
            strategy_file = f"instructions_{strategy.value}.md"
            parts.append(strategy_file)

        # Coin-specific instruction
        if coin:
            coin_file = f"instructions_{coin.symbol.lower()}.md"
            parts.append(coin_file)

        return self.load_modular(parts)

    def get_available_versions(self) -> list[str]:
        """
        Get list of available instruction versions.

        Returns:
            List of version identifiers (e.g., ["v1", "v2", "v3"])
        """
        versions = set()

        try:
            for file_path in self._base_path.glob("instructions_v*.md"):
                # Extract version from filename
                match = re.search(r"_v(\d+)", file_path.name)
                if match:
                    versions.add(f"v{match.group(1)}")
        except Exception:
            pass

        return sorted(list(versions), key=lambda x: int(x[1:]))

    def get_latest_version(self) -> str | None:
        """
        Get the latest instruction version.

        Returns:
            Latest version identifier or None if no versions found
        """
        versions = self.get_available_versions()
        return versions[-1] if versions else None

    def load_version(self, version: str) -> str | None:
        """
        Load specific version of instructions.

        Args:
            version: Version identifier (e.g., "v1", "v2")

        Returns:
            Instruction content or None if not found
        """
        filename = f"instructions_{version}.md"
        content = self.load(filename)

        if content is None:
            # Try base instructions as fallback
            return self.load("instructions.md")

        return content

    def migrate(
        self,
        content: str,
        from_version: str,
        to_version: str,
    ) -> str:
        """
        Migrate instruction content between versions.

        Args:
            content: Original instruction content
            from_version: Source version
            to_version: Target version

        Returns:
            Migrated instruction content
        """
        # Version migration rules
        migrations = {
            ("v1", "v2"): self._migrate_v1_to_v2,
            ("v2", "v3"): self._migrate_v2_to_v3,
        }

        migration_key = (from_version, to_version)
        migrator = migrations.get(migration_key)

        if migrator:
            return migrator(content)

        # No migration needed, return as-is
        self._logger.warning(
            "No migration path found",
            from_version=from_version,
            to_version=to_version,
        )
        return content

    def _migrate_v1_to_v2(self, content: str) -> str:
        """Migrate v1 instructions to v2 format."""
        # Add v2 header
        header = "# Trading Instructions v2\n\n"
        # Add multi-coin support note
        coin_support = (
            "\n\n## Multi-Coin Support\n\nThis version supports multiple cryptocurrencies.\n"
        )

        return header + content + coin_support

    def _migrate_v2_to_v3(self, content: str) -> str:
        """Migrate v2 instructions to v3 format."""
        # Add v3 header
        header = "# Trading Instructions v3 (Vision Enhanced)\n\n"
        # Add vision support note
        vision_support = "\n\n## Vision Analysis\n\nThis version supports chart image analysis.\n"

        return header + content + vision_support

    def render_template(
        self,
        template: str,
        **variables: Any,
    ) -> str:
        """
        Render instruction template with variables.

        Args:
            template: Template string with {variable} placeholders
            **variables: Variable values to substitute

        Returns:
            Rendered template string
        """
        return template.format(**variables)

    def render_template(
        self,
        template: str,
        defaults: dict[str, Any] | None = None,
        **variables: Any,
    ) -> str:
        """
        Render instruction template with variables and defaults.

        Args:
            template: Template string with {variable} placeholders
            defaults: Default values for missing variables
            **variables: Variable values to substitute

        Returns:
            Rendered template string
        """
        # Merge defaults with provided variables
        all_vars = {**(defaults or {}), **variables}

        try:
            return template.format(**all_vars)
        except KeyError as e:
            self._logger.warning(
                "Missing template variable",
                variable=str(e),
                available=list(all_vars.keys()),
            )
            # Return template with unfilled placeholders
            return template


__all__ = [
    "InstructionManager",
]
