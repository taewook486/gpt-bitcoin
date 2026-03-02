"""
Dependency injection container for the trading system.

This module provides a DI container using dependency-injector library
to manage component lifecycles and enable testability.
"""

from gpt_bitcoin.dependencies.container import Container, get_container

__all__ = ["Container", "get_container"]
