import pytest


def pytest_configure(config):
    """Register custom marks so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "live: marks tests that require a live API key and make real model calls",
    )
