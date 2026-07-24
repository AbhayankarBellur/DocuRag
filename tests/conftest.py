"""Pytest Configuration"""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def setup_database():
    """Setup test database"""
    # This would set up a test database
    # For now, we'll use SQLite in-memory
    yield
    # Cleanup would happen here
