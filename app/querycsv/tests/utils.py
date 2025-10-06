"""
CSV Data Tests Utilities
"""

import random
import uuid
from typing import Optional

import numpy as np
import pandas as pd
from django.db import models

from app.settings import MEDIA_ROOT
from core.abstracts.tests import TestsBase
from core.mock.models import Buster, BusterTag
from core.mock.serializers import BusterCsvSerializer
from lib.faker import fake
from querycsv.models import CsvUploadStatus, FieldMappingType, QueryCsvUploadJob
from querycsv.services import QueryCsvService
from utils.files import get_media_path
from utils.helpers import clean_list


class CsvDataTestsBase(TestsBase):
    """
    Base tests for Csv data services.

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

    Terms
    -----
        - repo: alias for Model.objects
        - objects: all instances of Model in database
    """

    model_class = Buster
    serializer_class = BusterCsvSerializer
    dataset_size = 5
    update_size = 3

    unique_field = "unique_name"
    """The field to test updates against."""

    def setUp(self) -> None:
        self.repo = self.model_class.objects
        self.serializer = self.serializer_class()
        self.service = QueryCsvService(serializer_class=self.serializer_class)

        return super().setUp()

    # Overrides
    #####################
    def get_create_params(self, **kwargs):
        return {"name": fake.title(), **kwargs}

    def get_update_params(self, obj: model_class, **kwargs):
        return {"name": fake.title(), **kwargs}

    # Initialization
    #####################
    def initialize_dataset(self):
        """Create mock objects, and any other setup tasks."""
        return self.create_mock_objects()

    def update_dataset(self):
        objects = list(self.repo.all())

        for _i in range(self.update_size):
            obj = random.choice(objects)
            objects.remove(obj)

            self.update_mock_object(obj=obj)

    # Utilities
    #####################
    def create_mock_object(self, **kwargs):
        return self.repo.create(**self.get_create_params(**kwargs))

    def create_mock_objects(self, amount: Optional[int] = None):
        """Create a set number of models."""

        if not amount:
            amount = self.dataset_size

        for _ in range(amount):
            self.create_mock_object()

    def update_mock_object(self, obj: model_class, **kwargs):
        """Update the object to differ from csv."""

        for key, value in self.get_update_params(obj=obj, **kwargs).items():
            setattr(obj, key, value)

        obj.save()

        return obj

    def get_unique_filepath(self, ext="csv"):
        return get_media_path(
            nested_path="tests/querydata/uploads/",
            filename=f"{uuid.uuid4()}.{ext}",
            create_path=True,
        )

    def df_to_csv(self, df: pd.DataFrame, filepath: Optional[str] = None):
        """
        Dump a dataframe to a csv, return filepath.
        """

        if filepath is None:
            filepath = self.filepath

        df.to_csv(filepath, index=False, mode="w")

        return filepath

    def data_to_df(self, data: list[dict]):
        """Convert output of serializer to dataframe."""
        # data_copy = [{**obj} for obj in data]

        data_copy = [self.serializer.json_to_flat(obj) for obj in data]

        # for model in data_copy:
        #     for key, value in model.items():
        #         if isinstance(value, list):
        #             if not islistinstance(value, dict):
        #                 model[key] = ",".join([str(v) for v in value])
        #             else:
        #                 model[key] =

        return pd.DataFrame.from_records(data_copy)

    def data_to_csv(self, data: list[dict]):
        """Convert list of dicts to a csv, return filepath."""

        df = self.data_to_df(data)
        return self.df_to_csv(df)

    def csv_to_df(self, path: str):
        """Convert csv at path to list of objects."""

        # Start by importing csv
        if path.endswith(".xlsx") or path.endswith(".xls"):
            df = pd.read_excel(path, dtype=str)
        else:
            df = pd.read_csv(path, dtype=str)

        df.replace(np.nan, "", inplace=True)

        return df

    # Custom assertions
    #####################
    def assertObjectsCount(self, count: int, msg=None):
        """Objects count in db should match given count."""
        self.assertEqual(self.repo.count(), count, msg=msg)

    def assertNoObjects(self):
        """Database should be empty."""

        self.assertObjectsCount(0)


class CsvDataM2OTestsBase(CsvDataTestsBase):
    """
    Test csv data with many-to-one fields.

    Overrides
    ---------
    Required:
        - model_class
        - serializer_class
        - m2o_model_class
        - m2o_selector
        - m2o_target_field
        - def get_create_params
        - def get_update_params
        - def get_m2o_create_params

    Optional:
        - dataset_size
        - unique_field
        - m2o_size
        - def create_mock_objects
    """

    model_class = Buster
    serializer_class = BusterCsvSerializer
    m2o_model_class = BusterTag
    m2o_size = 2

    m2o_serializer_key = "one_tag_str"
    """Field on the main serializer that points to child object."""

    m2o_model_key = "one_tag"
    """Field on the model object that points to child."""

    m2o_model_foreign_key = "name"
    """Field on child object whose value is used in serializer."""

    def setUp(self) -> None:
        super().setUp()

        self.m2o_repo = self.m2o_model_class.objects

    def get_m2o_create_params(self, **kwargs):
        return {"name": fake.title()}

    def create_mock_m2o_object(self, **kwargs):
        """Create Many to One object for testing."""

        return self.m2o_repo.create(**self.get_m2o_create_params(**kwargs))

    def initialize_dataset(self):
        super().initialize_dataset()

        m2o_objects = []
        for _i in range(self.m2o_size):
            m2o_objects.append(self.create_mock_m2o_object())

        for obj in self.repo.all():
            setattr(obj, self.m2o_serializer_key, random.choice(m2o_objects))

        # return self.repo.all()

    def update_dataset(self):
        objects = list(self.repo.all())
        m2os = list(self.m2o_repo.all())

        for _ in range(self.update_size):
            obj = random.choice(objects)
            objects.remove(obj)

            m2o = random.choice(m2os)
            self.update_mock_object(obj=obj, **{self.m2o_serializer_key: m2o})

    def clear_db(self) -> list:
        self.m2o_repo.all().delete()

        return super().clear_db()

    def assertObjectsM2OValidFields(self, df: pd.DataFrame):
        """Compare actual objects in the database with expected values in csv."""

        # Compare csv value with actual value
        for _index, row in df.iterrows():
            # Raw values in csv
            expected_value = row[self.m2o_serializer_key]

            if expected_value is None or str(expected_value).strip() == "":
                continue

            self.assertIsInstance(expected_value, str)
            query = row.to_dict()
            obj = self.repo.get(
                **{
                    k: v
                    for k, v in query.items()
                    if k != self.m2o_serializer_key
                    and k not in self.serializer.readonly_fields
                    and k not in self.serializer.any_related_fields
                    and k not in self.serializer.many_nested_fields
                    and k not in self.serializer.nested_fields
                }
            )

            m2o_obj = getattr(obj, self.m2o_model_key, {})
            actual_value = getattr(m2o_obj, self.m2o_model_foreign_key, None)

            self.assertEqual(expected_value, actual_value)


class CsvDataM2MTestsBase(CsvDataTestsBase):
    """
    Base utilities for testing many-to-many fields.

    Overrides
    ---------
    Required:
        - model_class
        - serializer_class
        - m2m_model_class
        - m2m_selector
        - m2m_target_field
        - def get_create_params
        - def get_update_params
        - def get_m2m_create_params

    Optional:
        - dataset_size
        - unique_field
        - m2m_size
        - m2m_update_size
    """

    model_class = Buster
    serializer_class = BusterCsvSerializer

    m2m_model_class = BusterTag
    m2m_size = 10
    m2m_update_size = 4
    m2m_assignment_max = 3

    m2m_serializer_key = "many_tags_str"
    """Field on the main serializer that points to child object."""

    m2m_model_key = "many_tags"
    """Field on the model object that points to child."""

    m2m_model_foreign_key = "name"
    """Field on child object whose value is used in serializer."""

    def setUp(self) -> None:
        super().setUp()

        self.m2m_repo = self.m2m_model_class.objects

        if self.m2m_serializer_key not in self.model_class.get_fields_list():
            self.m2m_model_selector = self.serializer.get_fields()[
                self.m2m_serializer_key
            ].source
        else:
            self.m2m_model_selector = self.m2m_serializer_key

    def get_m2m_create_params(self, **kwargs):
        return {"name": fake.title(), **kwargs}

    def initialize_dataset(self):
        super().initialize_dataset()

        m2m_objects = []
        for _i in range(self.m2m_size):
            m2m_objects.append(self.create_mock_m2m_object())

        for obj in self.repo.all():
            m2m_repo = getattr(obj, self.m2m_model_selector)

            assignment_count = random.randint(0, self.m2m_assignment_max)
            selected_m2m_objects = random.sample(m2m_objects, assignment_count)

            for _i, m2m_obj in enumerate(selected_m2m_objects):
                m2m_repo.add(m2m_obj)

            obj.save()

    def update_dataset(self):
        return super().update_dataset()

    def create_mock_m2m_object(self, **kwargs):
        return self.m2m_model_class.objects.create(
            **self.get_m2m_create_params(**kwargs)
        )

    def assertObjectsM2MValidFields(
        self, df: pd.DataFrame, objects_before: list[dict] = None
    ):
        """Compare expected objects in the csv with actual objects from database."""

        # Compare csv value with actual value
        for _index, row in df.iterrows():
            # Raw value in csv
            expected_value = row[self.m2m_serializer_key]

            if expected_value is None:
                continue

            # self.assertIsInstance(expected_value, str)
            csv_values = row.to_dict()
            query = None

            for key, value in csv_values.items():
                # Skip fields if they represent object, are none, or are for the serializer only
                if (
                    key in self.serializer.many_related_fields
                    or key in self.serializer.related_fields
                    or key in self.serializer.many_nested_fields
                    or key in self.serializer.nested_fields
                    or key in self.serializer.readonly_fields
                    or value is None
                    or value == ""
                    or key not in self.model_class.get_fields_list()
                ):
                    continue

                query_filter = models.Q(**{key: value})
                query = query & query_filter if query is not None else query_filter

            try:
                actual_obj = self.repo.get(query)
            except self.model_class.DoesNotExist as e:
                # Easier to debug
                print("Model not found with query:", query)
                raise e

            actual_related_objs = getattr(actual_obj, self.m2m_model_key).all()

            # Check database against csv
            expected_values = [str(v).strip() for v in str(expected_value).split(",")]
            expected_values = clean_list(expected_values)

            actual_values = [
                getattr(obj, self.m2m_model_foreign_key) for obj in actual_related_objs
            ]
            actual_values = clean_list(actual_values)

            self.assertListEqual(expected_values, actual_values)


class DownloadCsvTestsBase(CsvDataTestsBase):
    """
    Base utilities for download csv tests.

    Overrides
    ---------
    Required:
        - model_class
        - serializer_class
        - def get_create_params
        - def get_update_params

    Optional:
        - unique_field
        - dataset_size

    Terms
    -----
    - repo: alias for Model.objects
    - objects: all instances of Model in database
    """

    # def initialize_dataset(self):
    #     """Create database objects, return queryset."""

    #     self.create_mock_objects()
    #     self.assertObjectsCount(self.dataset_size)

    #     return self.repo.all()

    def assertValidCsv(self, filepath: str):
        """File at filepath should be a valid csv."""

        self.assertFileExists(filepath)
        self.assertStartsWith(filepath, MEDIA_ROOT)
        self.assertEndsWith(filepath, ".csv")

    def assertCsvHasFields(self, df: pd.DataFrame):
        """Iterate over csv data and verify with DB."""

        records = df.to_dict("records")

        for record in records:
            id = record.get("id")
            actual_object = self.repo.get_by_id(id)

            actual_serializer = self.serializer_class(actual_object)

            for field, expected_value in actual_serializer.data.items():
                # FIXME: This just skips nested objects
                if (
                    field
                    in self.serializer.nested_fields
                    + self.serializer.many_nested_fields
                ):
                    continue
                self.assertIn(field, record.keys())
                actual_value = record[field]

                if field in self.serializer.many_related_fields:
                    actual_values = [
                        val.strip() for val in str(actual_value).split(",")
                    ]
                    actual_values.sort()

                    expected_values = [str(val) for val in expected_value]
                    expected_values.sort()

                    self.assertListEqual(
                        clean_list(actual_values), clean_list(expected_values)
                    )
                elif field in self.serializer.nested_fields:
                    # TODO: Verify nested serialization
                    pass
                elif field in self.serializer.many_nested_fields:
                    # TODO: Verify many nested serialization
                    pass
                else:
                    self.assertEqual(str(actual_value or ""), str(expected_value or ""))


class UploadCsvTestsBase(CsvDataTestsBase):
    """
    Base utilities for upload data service.

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

    def setUp(self) -> None:
        super().setUp()

        self.filepath = self.get_unique_filepath()

    def create_objects(self):
        # Create test models
        self.assertNoObjects()
        self.create_mock_objects()

        objects = self.repo.all()
        self.assertEqual(objects.count(), self.dataset_size)

        return objects

    def dump_csv(self, query: models.QuerySet):
        """Manually Print query to csv, independent of services."""

        data = self.serializer_class(query, many=True).data
        self.df = self.data_to_df(data)
        self.df = self.df.fillna("")
        self.df_to_csv(self.df)

    def initialize_csv_data(self, clear_db=True):
        """Create csv with data, then clear the database."""

        # Initialize data
        self.initialize_dataset()
        objects = self.repo.all()
        objects_before = objects.values()
        self.dump_csv(objects)

        # Clear database
        if clear_db:
            self.clear_db()

        return objects_before

    def clear_db(self) -> list:
        """Save list of current objects and clear the database."""

        self.repo.all().delete()
        self.assertNoObjects()

    def assertUploadPayload(
        self,
        payload: list[dict],
        custom_field_maps: list[FieldMappingType] | None = None,
        validate_res=True,
        **kwargs,
    ):
        """Given a list of flattened dicts, will convert to csv and upload."""

        self.data_to_csv(payload)

        success, failed = self.service.upload_csv(
            self.filepath, custom_field_maps=custom_field_maps, **kwargs
        )

        if not validate_res:
            return success, failed

        self.assertLength(success, len(payload), failed)
        self.assertLength(failed, 0)

        return success, failed

    def assertUploadJob(self, job: QueryCsvUploadJob, validate_res=True):
        """Should successfully upload and process a job."""

        success, failed = self.service.upload_from_job(job)

        if not validate_res:
            return success, failed

        job.refresh_from_db()

        self.assertLength(failed, 0)
        self.assertEqual(job.status, CsvUploadStatus.SUCCESS)
        self.assertIsNotNone(job.report)
        self.assertIsNone(job.error)

    def assertObjectsExist(self, pre_queryset: list, msg=None):
        """Objects represented in queryset should exist in the database."""
        self.assertObjectsCount(self.dataset_size, msg=msg)

        for expected_obj in pre_queryset:
            query = self.repo.filter(**expected_obj)
            self.assertTrue(query.exists(), msg=msg)

    def assertObjectsHaveFields(self, expected_objects: list[dict]):
        """
        Check if the actual object has expected fields.

        Verify by comparing the serialized representation for before and after
        the upload - both should have the save value for writable fields.
        """

        for expected_obj in expected_objects:
            expected_serializer = self.serializer_class(data=expected_obj)
            self.assertValidSerializer(expected_serializer)

            # Search for object matching query
            query = {
                k: v
                for k, v in expected_obj.items()
                if k in self.serializer.writable_fields
                and k not in self.serializer.any_related_fields
                and k in self.model_class.get_fields_list()
                and v is not None
                and v != ""
            }

            # Extra parsing for query
            for k, v in query.items():
                if isinstance(v, str):
                    query[k] = v.strip()

            # Validate object fields
            actual_object = self.repo.get(**query)
            actual_serializer = self.serializer_class(actual_object)

            for field in self.serializer.writable_fields:
                if (
                    field not in expected_serializer.data.keys()
                    and field not in actual_serializer.data.keys()
                ):
                    continue

                expected_value = expected_serializer.data[field]
                actual_value = actual_serializer.data[field]

                if isinstance(expected_value, str):
                    expected_value.strip()

                    self.assertFalse(str(expected_value).startswith(" "))
                    self.assertFalse(str(expected_value).endswith(" "))

                    self.assertFalse(str(actual_value).startswith(" "))
                    self.assertFalse(str(actual_value).endswith(" "))

                self.assertEqual(expected_value, actual_value)
