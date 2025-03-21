"""
Tests for core views and health checks.
"""

from core.abstracts.tests import ApiTestsBase


class CoreViewTests(ApiTestsBase):
    """Test the Core views."""

    def test_health_check(self):
        """Should return 200."""

        self.assertOk("core:health")

    def test_index_view(self):
        """Should return 200."""

        self.assertOk("core:index")
