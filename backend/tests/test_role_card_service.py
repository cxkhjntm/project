"""Tests for role card service."""

import pytest

from app.services.role_card_service import RoleCardService


@pytest.fixture
def role_card_service() -> RoleCardService:
    """Create role card service instance."""
    return RoleCardService()


class TestRoleCardService:
    """Test role card service CRUD operations."""

    def test_service_instantiation(self, role_card_service: RoleCardService) -> None:
        """Test that service can be instantiated."""
        assert role_card_service is not None
