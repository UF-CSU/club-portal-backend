"""
Import/upload data tests.
"""

import json
import os
import uuid
from unittest.mock import patch

from django.contrib.postgres.aggregates import StringAgg
from django.db import models

from core.mock.models import BusterTag
from core.mock.serializers import BusterTagNestedSerializer
from lib.faker import fake
from querycsv.models import CsvUploadStatus, FieldMappingType, QueryCsvUploadJob
from querycsv.services import QueryCsvService
from querycsv.tests.utils import (
    CsvDataM2MTestsBase,
    CsvDataM2OTestsBase,
    UploadCsvTestsBase,
)
from utils.testing import set_mock_return_image


class UploadCsvTests(UploadCsvTestsBase):
    """
    Test uploading data from a csv.

    Overrides
    ---------
    Required:
        - model_class
        - serializer_class
        - def get_create_params
        - def get_update_params

    Optional:
        - dataset_size
        - unique_field
    """

    def test_create_objects_from_csv(self):
        """Should be able to take csv and create models."""

        # Initialize data
        objects_before = self.initialize_csv_data()

        # Call service upload function
        _, failed = self.service.upload_csv(path=self.filepath)

        # Validate database
        self.assertObjectsExist(objects_before, failed)
        self.assertObjectsHaveFields(objects_before)

    def test_update_objects_from_csv(self):
        # Initialize data
        objects_before = self.initialize_csv_data(clear_db=False)

        for obj in self.repo.all():
            self.update_mock_object(obj)

        # Call service upload function
        self.service.upload_csv(path=self.filepath)

        # Validate database
        self.assertObjectsExist(objects_before)
        self.assertObjectsHaveFields(objects_before)

    def test_upload_csv_bad_fields(self):
        """Should create objects and ignore bad fields."""

        # Initialize csv, add invalid column
        objects_before = self.initialize_csv_data()
        self.df["Invalid field"] = "bad value"
        self.df_to_csv(self.df)

        self.assertTrue("Invalid field" in list(self.df.columns))

        self.service.upload_csv(path=self.filepath)

        # Validate database
        self.assertObjectsExist(objects_before)
        self.assertObjectsHaveFields(objects_before)

    def test_upload_csv_update_objects(self):
        """Uploading a csv should update objects."""

        # Prep data, create csv
        objects_before = self.initialize_csv_data(clear_db=False)

        updated_records = []

        for obj in objects_before:
            payload = {self.unique_field: obj[self.unique_field]}
            payload = self.get_update_params(obj, **payload)
            updated_records.append(payload)

        self.data_to_csv(updated_records)

        # Upload CSV
        self.service.upload_csv(path=self.filepath)

        # Validate data
        self.assertObjectsHaveFields(updated_records)

    def test_upload_csv_spaces(self):
        """Should remove pre/post spaces from fields before updating/creating."""

        # Prep data, create csv
        objects_before = self.initialize_csv_data(clear_db=False)

        updated_records = []

        for obj in objects_before:
            payload = {self.unique_field: f"  {obj[self.unique_field]}  "}
            payload = self.get_update_params(obj, **payload)
            updated_records.append(payload)

        self.data_to_csv(updated_records)
        self.assertObjectsExist(objects_before)

        # Upload CSV
        self.service.upload_csv(path=self.filepath)

        # Validate data
        self.assertObjectsHaveFields(updated_records)

    @patch("requests.get")
    def test_upload_csv_create_images(self, mock_get):
        """Should download images from url when uploading csv to create objects."""

        set_mock_return_image(mock_get)

        payload = {
            "name": fake.title(),
            "image": "https://example.com/image.png",
        }

        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()

        self.assertTrue(obj.image)
        self.assertEqual(obj.image.width, 300)
        self.assertEqual(obj.image.height, 300)

    @patch("requests.get")
    def test_upload_csv_update_images(self, mock_get):
        """Should download images from url when updating objects with csv."""

        set_mock_return_image(mock_get)

        default_payload = {
            "name": fake.title(),
            "unique_name": uuid.uuid4(),
        }

        self.repo.create(**default_payload)

        payload = {
            **default_payload,
            "image": "https://example.com/image.png",
        }

        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()

        self.assertTrue(obj.image)
        self.assertEqual(obj.image.width, 300)
        self.assertEqual(obj.image.height, 300)

    def test_upload_csv_skip_fields(self):
        """Uploading a csv should allow option to skip fields."""

        payload = {
            "name": fake.title(),
            "unique_name": uuid.uuid4().__str__(),
        }
        field_mappings = [{"column_name": "unique_name", "field_name": "SKIP"}]

        self.assertUploadPayload([payload], custom_field_maps=field_mappings)

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()

        self.assertNotEqual(obj.unique_name, payload["unique_name"])

    def test_upload_bad_unique_fields(self):
        """Uploading a csv with missmatched unique fields should not add buster."""

        payload = [
            {
                "name": fake.title(),
                "unique_name": uuid.uuid4().__str__(),
                "unique_email": fake.safe_email(),
            },
            {
                "name": fake.title(),
                "unique_name": uuid.uuid4().__str__(),
                "unique_email": fake.safe_email(),
            },
        ]

        # Situation 1: Missmatched unique fields, raise error
        # Example: unique_email matches, but unique_name does not
        self.repo.create(
            name=fake.title(),
            unique_name=uuid.uuid4(),
            unique_email=payload[0]["unique_email"],
        )

        # Situation 2: Search one unique field, update the other
        # Examle: unique_name matches, but unique_email does not exist in the database
        self.repo.create(
            name=fake.title(),
            unique_name=payload[1]["unique_name"],
        )

        success, failed = self.assertUploadPayload(payload, validate_res=False)
        self.assertEqual(self.repo.count(), 2)
        self.assertLength(success, 1)
        self.assertLength(failed, 1)

    def test_uploading_unique_null_fields(self):
        """When uploading csv, should handle unique null fields."""

        payload = [
            {
                "name": fake.title(),
                "unique_email": fake.safe_email(),
            },
        ]

        # Situation 1: Optional unique field is null, create new object
        # Example: unique_name is null in db, and unique_name is provided in csv,
        # ignore the null value and continue creating new object
        obj = self.repo.create(name=fake.title(), unique_email=None)

        self.assertUploadPayload(payload)
        self.assertEqual(self.repo.count(), 2)

        # Should have created new object, not update existing one
        obj.refresh_from_db()
        self.assertIsNone(obj.unique_email)
        self.assertTrue(self.repo.filter(unique_email=payload[0]["unique_email"]))

    def test_handles_parsing_error(self):
        """Should safely handle an error that doesn't relate to the serializer."""

        # Error strategy: unknown extension and file not found
        self.filepath = self.filepath.replace(".csv", ".abc")

        success, failed = self.service.upload_csv(self.filepath)
        self.assertIsInstance(failed, Exception)
        self.assertLength(success, 0)


class UploadJsonTests(UploadCsvTestsBase):
    """Test uploading json files."""

    def test_upload_json_many_str(self):
        """Should be able to upload json file."""

        filepath = self.get_unique_filepath(ext="json")
        payload = [
            {
                "name": fake.title(),
                "unique_name": uuid.uuid4().__str__(),
                "many_tags_str": ["tag1", "tag2"],
            }
        ]

        dir = os.path.dirname(filepath)
        os.makedirs(dir, exist_ok=True)

        with open(filepath, mode="w+") as f:
            json.dump(payload, f, indent=4)

        success, failed = self.service.upload_csv(path=filepath)
        self.assertEqual(len(success), 1, failed)
        self.assertEqual(len(failed), 0)
        self.assertEqual(self.repo.count(), 1)

        obj = self.repo.first()
        self.assertEqual(obj.name, payload[0]["name"])
        self.assertEqual(obj.unique_name, payload[0]["unique_name"])
        self.assertEqual(obj.many_tags.count(), 2)

        self.assertTrue(obj.many_tags.filter(name="tag1").exists())
        self.assertTrue(obj.many_tags.filter(name="tag2").exists())

    def test_upload_json_many_nested(self):
        """Should be able to upload json file."""

        filepath = self.get_unique_filepath(ext="json")
        payload = [
            {
                "name": fake.title(),
                "unique_name": uuid.uuid4().__str__(),
                "many_tags_nested": [
                    {
                        "name": fake.title(),
                        "color": fake.color(),
                    },
                    {
                        "name": fake.title(),
                        "color": fake.color(),
                    },
                    {
                        "name": fake.title(),
                        "color": fake.color(),
                    },
                ],
            }
        ]

        dir = os.path.dirname(filepath)
        os.makedirs(dir, exist_ok=True)

        with open(filepath, mode="w+") as f:
            json.dump(payload, f, indent=4)

        success, failed = self.service.upload_csv(path=filepath)
        self.assertEqual(len(success), 1, failed)
        self.assertEqual(len(failed), 0)
        self.assertEqual(self.repo.count(), 1)

        obj = self.repo.first()
        self.assertEqual(obj.name, payload[0]["name"])
        self.assertEqual(obj.unique_name, payload[0]["unique_name"])
        self.assertEqual(obj.many_tags.count(), 3)

        for tag_data in payload[0]["many_tags_nested"]:
            tag = BusterTag.objects.get(name=tag_data["name"])
            self.assertEqual(tag.color, tag_data["color"])


class UploadCsvJobTests(UploadCsvTestsBase):
    """Tests for uploading with QSCsv Model."""

    def test_upload_from_job(self):
        """Should upload and process csv from model."""

        # Initialize data
        objects_before = self.initialize_csv_data(clear_db=False)

        # Update fields after create csv
        for obj in self.repo.all():
            self.update_mock_object(obj)

        # Upload csv via service
        job = QueryCsvUploadJob.objects.create(
            filepath=self.filepath,
            serializer_class=self.serializer_class,
        )
        QueryCsvService.upload_from_job(job)

        # Validate database
        self.assertObjectsExist(objects_before)
        self.assertObjectsHaveFields(objects_before)

    def test_upload_custom_fields(self):
        """Should process csv with custom field mappings."""

        objects_before = self.initialize_csv_data()

        # Rename csv field
        self.df.rename(columns={"name": "Test Value"}, inplace=True)
        self.df_to_csv(self.df, self.filepath)

        # Create and upload job
        job = QueryCsvUploadJob.objects.create(
            serializer_class=self.serializer_class, filepath=self.filepath
        )
        job.add_field_mapping(column_name="Test Value", field_name="name")
        job.refresh_from_db()

        QueryCsvService.upload_from_job(job)

        # Validate database
        self.assertObjectsExist(pre_queryset=objects_before)
        self.assertObjectsHaveFields(expected_objects=objects_before)

    def test_failed_job(self):
        """Should correctly handle a failed job."""

        self.initialize_csv_data()

        job = QueryCsvUploadJob.objects.create(
            serializer_class=self.serializer_class, filepath=self.filepath
        )
        # Error strategy: invalid field mapping
        job.custom_field_mappings = {"fields": ["Some invalid input"]}
        job.save()

        success, failed = self.assertUploadJob(job, validate_res=False)
        self.assertIsInstance(failed, Exception)
        self.assertLength(success, 0)
        self.assertEqual(job.status, CsvUploadStatus.FAILED)
        self.assertIsNotNone(job.error)
        self.assertFalse(job.report)


class UploadCsvM2OFieldsTests(UploadCsvTestsBase, CsvDataM2OTestsBase):
    """Test uploading csvs for models with many-to-one fields."""

    def test_upload_csv_m2o_fields(self):
        """
        Should present Many-to-One (FK) fields according to serializer.

        Check by comparing the serialized representation before and after
        the upload - both should have the save value for writable fields.
        """

        # Initialize data
        objects_before = self.initialize_csv_data()

        # Call upload function
        self.service.upload_csv(path=self.filepath)

        # Validate database
        self.assertObjectsHaveFields(objects_before)
        self.assertIn(self.m2o_serializer_key, list(self.df.columns))

        self.assertObjectsM2OValidFields(self.df)

    def test_upload_csv_m2o_fields_update(self):
        """Should update models with Many-to-One fields."""

        # Initialize data
        objects_before = self.initialize_csv_data(clear_db=False)

        # Update fields after create csv
        for obj in self.repo.all():
            self.update_mock_object(obj)

        # Call upload function
        self.service.upload_csv(path=self.filepath)

        # Validate database
        self.assertObjectsHaveFields(objects_before)
        self.assertIn(self.m2o_serializer_key, list(self.df.columns))

        self.assertObjectsM2OValidFields(self.df)


class UploadCsvM2MFieldsTests(UploadCsvTestsBase, CsvDataM2MTestsBase):
    """Test uploading csvs for models with many-to-many fields."""

    def test_upload_csv_m2m_fields(self):
        """When csv is uploaded, m2m fields should be handled properly."""

        # Initialize data
        objects_before = self.initialize_csv_data()

        # Upload csv using service
        success, failed = self.service.upload_csv(path=self.filepath)
        self.assertLength(success, self.dataset_size, failed)
        self.assertLength(failed, 0)

        # Validate results
        self.assertObjectsHaveFields(objects_before)
        self.assertIn(self.m2m_serializer_key, list(self.df.columns))

        self.assertObjectsM2MValidFields(self.df)

    def test_upload_csv_m2m_fields_spaces(self):
        """When csv is uploaded, m2m fields should be stripped of leading/trailing spaces."""

        objects_before = self.initialize_csv_data()

        # Iterate through csv, manually add spacing
        for _i, row in self.df.iterrows():
            pre_value = row[self.m2m_serializer_key]
            pre_values = pre_value.split(",")
            modified_value = "  ,  ".join(pre_values)
            row[self.m2m_serializer_key] = modified_value

        self.df_to_csv(self.df)

        # Upload csv using service
        success, failed = self.service.upload_csv(path=self.filepath)
        self.assertLength(success, self.dataset_size, failed)
        self.assertLength(failed, 0)

        # Validate results
        self.assertObjectsHaveFields(objects_before)
        self.assertIn(self.m2m_serializer_key, list(self.df.columns))

        self.assertObjectsM2MValidFields(self.df)

    def test_upload_csv_m2m_update_fields(self):
        """When csv is uploaded, should update objects with many-to-many fields."""

        # Initialize data
        objects_before = self.initialize_csv_data(clear_db=False)

        # Update fields after create csv
        self.update_dataset()

        objects_before = list(
            self.repo.all()
            .annotate(
                pre_objs_count=models.Count(self.m2m_model_key),
                pre_objs=StringAgg(
                    models.F(f"{self.m2m_model_key}__{self.m2m_model_foreign_key}"),
                    distinct=True,
                    delimiter=",",
                ),
            )
            .values()
        )

        # Upload csv using service
        success, failed = self.service.upload_csv(path=self.filepath)
        self.assertLength(success, self.dataset_size, failed)
        self.assertLength(failed, 0)

        # Validate results
        self.assertEqual(self.repo.all().count(), self.dataset_size)
        expected_objects = list(self.df.to_dict("records"))

        self.assertObjectsHaveFields(expected_objects)
        self.assertIn(self.m2m_serializer_key, list(self.df.columns))
        self.assertTrue(
            self.m2m_repo.all().count() <= self.m2m_size + self.m2m_update_size,
            f"Expected at most {self.m2m_size + self.m2m_update_size} M2M objects, "
            f"but {self.m2m_repo.all().count()} were created.",
        )

        self.assertObjectsM2MValidFields(self.df, objects_before)

    def test_upload_csv_m2m_fields_commas(self):
        """Uploading a M2M object with a comma should work if wrapped in quotes."""

        payload = {
            "name": fake.title(),
            "many_tags_str": 'one,two,"three, four, five"',
        }
        self.assertUploadPayload([payload])

        self.assertEqual(self.m2m_repo.count(), 3)
        q1 = self.m2m_repo.filter(name="one")
        self.assertTrue(q1.exists())

        q2 = self.m2m_repo.filter(name="two")
        self.assertTrue(q2.exists())

        q3 = self.m2m_repo.filter(name="three, four, five")
        self.assertTrue(q3.exists())


class UploadCsvNestedFieldsTests(UploadCsvTestsBase):
    """Test uploading csvs with nested fields."""

    serializer_single_nested_key = "one_tag_nested"
    serializer_many_nested_key = "many_tags_nested"

    nested_model_class = BusterTag
    nested_serializer_class = BusterTagNestedSerializer

    def setUp(self):
        self.nested_repo = self.nested_model_class.objects
        return super().setUp()

    def test_upload_csv_create_single_nested(self):
        """Uploading a csv with a nested single field should work."""

        payload = {
            "name": fake.title(),
            "one_tag_nested.name": fake.title(),
        }
        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(self.nested_repo.count(), 1)
        nested_obj = self.nested_repo.first()
        self.assertEqual(nested_obj.name, payload["one_tag_nested.name"])

    def test_upload_csv_update_single_nested(self):
        """Uploading a csv with a nested single field should update appropriate objects."""

        default_payload = {
            "unique_name": uuid.uuid4(),
            "name": fake.title(),
        }

        self.repo.create(**default_payload)

        payload = {
            **default_payload,
            "one_tag_nested.name": fake.title(),
        }
        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(self.nested_repo.count(), 1)
        nested_obj = self.nested_repo.first()
        self.assertEqual(nested_obj.name, payload["one_tag_nested.name"])

    def test_upload_csv_create_many_nested(self):
        """Uploading a csv with nested many fields should work."""

        payload = {
            "name": fake.title(),
            "many_tags_nested[0].name": fake.title(),
            "many_tags_nested[0].color": fake.color(),
            "many_tags_nested[1].name": fake.title(),
            "many_tags_nested[1].color": fake.color(),
        }
        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(self.nested_repo.count(), 2)

        nested_obj = self.nested_repo.filter(name=payload["many_tags_nested[0].name"])
        self.assertTrue(nested_obj.exists())
        nested_obj = nested_obj.first()
        self.assertEqual(nested_obj.color, payload["many_tags_nested[0].color"])

        nested_obj = self.nested_repo.filter(name=payload["many_tags_nested[1].name"])
        self.assertTrue(nested_obj.exists())
        nested_obj = nested_obj.first()
        self.assertEqual(nested_obj.color, payload["many_tags_nested[1].color"])

    def test_upload_csv_update_many_nested(self):
        """Uploading a csv with nested many fields should update the object."""

        default_payload = {
            "unique_name": uuid.uuid4(),
            "name": fake.title(),
        }

        self.repo.create(**default_payload)

        payload = {
            **default_payload,
            "many_tags_nested[0].name": fake.title(),
            "many_tags_nested[0].color": fake.color(),
            "many_tags_nested[1].name": fake.title(),
            "many_tags_nested[1].color": fake.color(),
        }
        self.assertUploadPayload([payload])

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(self.nested_repo.count(), 2)

        nested_obj = self.nested_repo.filter(name=payload["many_tags_nested[0].name"])
        self.assertTrue(nested_obj.exists())
        nested_obj = nested_obj.first()
        self.assertEqual(nested_obj.color, payload["many_tags_nested[0].color"])

        nested_obj = self.nested_repo.filter(name=payload["many_tags_nested[1].name"])
        self.assertTrue(nested_obj.exists())
        nested_obj = nested_obj.first()
        self.assertEqual(nested_obj.color, payload["many_tags_nested[1].color"])

    def test_upload_csv_mapping(self):
        """Should upload csv payload with mapping."""

        payload = {
            "buster": fake.title(),
            "tag_name": fake.title(),
            "tag_color": fake.color(),
        }
        mappings: list[FieldMappingType] = [
            {"column_name": "buster", "field_name": "name"},
            {"column_name": "tag_name", "field_name": "many_tags_nested[0].name"},
            {"column_name": "tag_color", "field_name": "many_tags_nested[0].color"},
        ]

        self.assertUploadPayload([payload], custom_field_maps=mappings)

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["buster"])

        self.assertEqual(self.nested_repo.count(), 1)
        nested_obj = self.nested_repo.filter(name=payload["tag_name"])
        self.assertTrue(nested_obj.exists())
        nested_obj = nested_obj.first()
        self.assertEqual(nested_obj.color, payload["tag_color"])

    # def test_upload_csv_with_n_field(self):
    #     """Should upload csv payload including an "n-field"."""

    #     payload = {
    #         "name": fake.title(),
    #         "many_tags_nested[n].name": fake.title(),
    #         "many_tags_nested[n].color": fake.color(),
    #     }

    #     self.assertUploadPayload([payload])

    #     self.assertEqual(self.repo.count(), 1)
    #     obj = self.repo.first()
    #     self.assertEqual(obj.name, payload["name"])

    #     self.assertEqual(self.nested_repo.count(), 1)
    #     nested_obj = self.nested_repo.filter(name=payload["many_tags_nested[n].name"])
    #     self.assertTrue(nested_obj.exists())
    #     nested_obj = nested_obj.first()
    #     self.assertEqual(nested_obj.color, payload["many_tags_nested[n].color"])
