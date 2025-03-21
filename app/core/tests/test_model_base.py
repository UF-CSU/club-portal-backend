"""
Unit tests for core base models.
"""

from core.abstracts.tests import TestsBase
from core.mock.models import Buster
from lib.faker import fake


class BaseModelTests(TestsBase):
    """Base model unit tests."""

    model_class = Buster

    def setUp(self):
        self.repo = self.model_class.objects

        return super().setUp()

    def create_test_object(self, **kwargs):
        payload = {"name": fake.title(3), **kwargs}

        return self.repo.create(**payload)

    def create_test_objects(self, count=2, **kwargs):
        objs = [self.create_test_object(**kwargs).id for _ in range(count)]
        return self.repo.filter(id__in=objs)

    def test_create_model(self):
        """Should create model."""

        self.assertEqual(self.repo.count(), 0)
        self.repo.create(name=fake.sentence(3))
        self.assertEqual(self.repo.count(), 1)

    def test_find_one(self):
        """Should find one object, or return None"""

        name = fake.sentence(3)
        self.create_test_object(name=name)
        self.create_test_object(name=name)

        self.assertIsInstance(self.repo.find_one(name=name), self.model_class)

        not_name = fake.sentence(2)
        self.assertIsNone(self.repo.find_one(name=not_name))

    def test_find_by_id(self):
        """Should find one by id, or return None."""

        name = fake.sentence(3)
        qs = self.create_test_objects(2, name=name)
        obj1 = qs.first()

        self.assertIsInstance(self.repo.find_by_id(id=obj1.id), self.model_class)
        self.assertIsNone(self.repo.find_by_id(id=-1))

    def test_find(self):
        """Should find objects matching query, or return none."""

        name = fake.sentence(3)
        qs = self.create_test_objects(2, name=name)
        obj1 = qs.first()

        self.assertEqual(self.repo.find(name=name).count(), 2)
        self.assertEqual(self.repo.find(id=obj1.id).count(), 1)

        not_name = fake.sentence(2)
        self.assertIsNone(self.repo.find(name=not_name))

    def test_filter_one(self):
        """Should return first item from filter, or none."""

        name = fake.sentence(3)
        self.create_test_objects(2, name=name)

        self.assertIsInstance(self.repo.find_one(name=name), self.model_class)

        not_name = fake.sentence(2)
        self.assertIsNone(self.repo.find_one(name=not_name))

    def test_get_by_id(self):
        """Should get object by id."""

        qs = self.create_test_objects(3)
        obj = qs.first()

        self.assertIsInstance(self.repo.get_by_id(obj.id), self.model_class)

        with self.assertRaises(self.model_class.DoesNotExist):
            self.repo.get_by_id(-1)

    def test_get_or_create(self):
        """Should get object if exists, create otherwise."""

        name = fake.sentence(3)
        self.assertEqual(self.repo.filter(name=name).count(), 0)

        obj, created = self.repo.get_or_create(name=name)

        self.assertEqual(obj.name, name)
        self.assertTrue(created)
        self.assertEqual(self.repo.filter(name=name).count(), 1)

        obj2, created2 = self.repo.get_or_create(name=name)
        self.assertEqual(obj2.name, name)
        self.assertFalse(created2)
        self.assertEqual(self.repo.filter(name=name).count(), 1)

    def test_update_one(self):
        """Should update one object."""

        name = fake.sentence(3)
        qs = self.create_test_objects(3, name=name)
        obj = qs.first()

        changed_name = "changed-" + name
        self.assertEqual(self.repo.filter(name=changed_name).count(), 0)
        self.repo.update_one(obj.id, name=changed_name)
        self.assertEqual(self.repo.filter(name=changed_name).count(), 1)

        self.assertIsNone(self.repo.update_one(-1, name=changed_name))
        self.assertEqual(self.repo.filter(name=changed_name).count(), 1)

    def test_update_many(self):
        """Should update multiple objects based on query."""

        name1 = fake.sentence(3)
        name2 = fake.sentence(4)

        self.create_test_objects(2, name=name1)
        self.create_test_objects(2, name=name2)

        changed_name = "changed-" + name1
        self.assertEqual(self.repo.filter(name=changed_name).count(), 0)

        res = self.repo.update_many(query={"name": name1}, name=changed_name)
        self.assertEqual(res.count(), 2)

        self.assertEqual(self.repo.filter(name=name1).count(), 0)
        self.assertEqual(self.repo.filter(name=changed_name).count(), 2)
        self.assertEqual(self.repo.filter(name=name2).count(), 2)

    def test_delete_one(self):
        """Should delete object by id."""

        qs = self.create_test_objects(3)
        obj = qs.first()

        res = self.repo.delete_one(obj.id)
        self.assertIsInstance(res, self.model_class)
        self.assertEqual(self.repo.all().count(), 2)

        res2 = self.repo.delete_one(-1)
        self.assertIsNone(res2)
        self.assertEqual(self.repo.all().count(), 2)

    def test_delete_many(self):
        """Should delete objects based on query."""

        name1 = fake.sentence(3)
        name2 = fake.sentence(4)

        self.create_test_objects(2, name=name1)
        self.create_test_objects(2, name=name2)

        self.assertEqual(self.repo.count(), 4)

        res = self.repo.delete_many(name=name1)
        self.assertEqual(len(res), 2)
        self.assertEqual(self.repo.count(), 2)

        res2 = self.repo.delete_many(name=name1)
        self.assertEqual(len(res2), 0)
        self.assertEqual(self.repo.count(), 2)
