from core.abstracts.services import ServiceBase
from core.abstracts.tests import TestsBase
from core.mock.models import Buster
from core.mock.utils import create_test_buster


class BaseServiceTests(TestsBase):
    """Unit tests for base service."""

    model_class = Buster

    def setUp(self):
        class BusterService(ServiceBase):
            """Create temp service for testing."""

            model = Buster
            str_lookup = "name"

        self.service_class = BusterService

        return super().setUp()

    def test_instantiate_service(self):
        """Should create new instance of service."""

        obj = create_test_buster()

        self.assertIsInstance(self.service_class(obj), self.service_class)
        self.assertIsInstance(self.service_class(obj.id), self.service_class)
        self.assertIsInstance(self.service_class(str(obj.id)), self.service_class)
        self.assertIsInstance(self.service_class(obj.name), self.service_class)
