"""
CSV Download Tests
"""

from lib.faker import fake
from querycsv.tests.utils import (
    CsvDataM2MTestsBase,
    CsvDataM2OTestsBase,
    DownloadCsvTestsBase,
)
from utils.helpers import clean_list, str_to_list


class DownloadDataTests(DownloadCsvTestsBase):
    """Unit tests for download csv data."""

    def test_download_model_csv(self):
        """Should download a csv listing objects for model."""

        # Create csv using service
        self.initialize_dataset()
        qs = self.repo.all()

        filepath = self.service.download_csv(queryset=qs)
        self.assertValidCsv(filepath)

        # Check csv
        df = self.csv_to_df(filepath)
        self.assertEqual(len(df.index), self.dataset_size)

        expected_fields = self.serializer.readable_fields
        expected_fields.sort()

        actual_fields = list(df.columns)
        actual_fields.sort()

        self.assertListEqual(expected_fields, actual_fields)

        # Verify contact fields in csv
        self.assertCsvHasFields(df)


class DownloadCsvM2OFieldsTests(DownloadCsvTestsBase, CsvDataM2OTestsBase):
    """Unit tests for testing downloaded csv many-to-one fields."""

    def test_download_csv_m2o_fields(self):
        """Should be able to download models with many-to-one fields."""

        # Create csv using service
        self.initialize_dataset()
        qs = self.repo.all()

        filepath = self.service.download_csv(queryset=qs)
        self.assertValidCsv(filepath)

        # Check csv
        df = self.csv_to_df(filepath)
        self.assertCsvHasFields(df)

        # For each row, check the many-to-one field
        for _index, row in df.iterrows():
            obj_id = row["id"]
            expected_obj = self.repo.get_by_id(obj_id)

            expected_m2o_obj = getattr(expected_obj, self.m2o_model_key)

            if expected_m2o_obj is None:
                expected_value = None
            else:
                expected_value = getattr(expected_m2o_obj, self.m2o_model_foreign_key)

            actual_value = row[self.m2o_serializer_key]
            if actual_value == "":
                actual_value = None

            self.assertEqual(actual_value, expected_value)


class DownloadCsvM2MFieldsStrTests(DownloadCsvTestsBase, CsvDataM2MTestsBase):
    """Unit tests for testing downloaded csv many-to-many fields with str slug."""

    def test_download_csv_m2m_fields(self):
        """Should be able to download models with many-to-many fields."""

        # Create csv using service
        self.initialize_dataset()
        qs = self.repo.all()

        filepath = self.service.download_csv(queryset=qs)
        self.assertValidCsv(filepath)

        # Check csv
        df = self.csv_to_df(filepath)
        self.assertCsvHasFields(df)

        # For each row, check the many-to-one field
        for _index, row in df.iterrows():
            obj_id = row["id"]
            expected_obj = self.repo.get_by_id(obj_id)

            expected_m2m_objs = getattr(expected_obj, self.m2m_model_selector)
            expected_values = clean_list(
                [
                    str(getattr(obj, self.m2m_model_foreign_key))
                    for obj in expected_m2m_objs.all()
                ]
            )

            actual_value_raw = str(row[self.m2m_serializer_key])
            actual_values = clean_list(
                [str(v).strip() for v in actual_value_raw.split(",")]
            )

            self.assertListEqual(actual_values, expected_values)

    def test_download_csv_m2m_commas(self):
        """Should be able to download tags if they include commas."""

        self.initialize_dataset()

        for i, tag in enumerate(list(self.m2m_repo.all())):
            if i % 2 != 0:
                continue

            tag.name = tag.name + f", {fake.title()}"
            tag.save()

        qs = self.repo.all()

        filepath = self.service.download_csv(queryset=qs)
        self.assertValidCsv(filepath)

        df = self.csv_to_df(filepath)

        for _index, row in df.iterrows():
            obj_id = row["id"]
            expected_obj = self.repo.get_by_id(obj_id)

            expected_m2m_objs = getattr(expected_obj, self.m2m_model_selector)
            expected_values = clean_list(
                [
                    str(getattr(obj, self.m2m_model_foreign_key))
                    for obj in expected_m2m_objs.all()
                ]
            )

            actual_value_raw = str(row[self.m2m_serializer_key])
            actual_values = str_to_list(actual_value_raw)

            self.assertListEqual(actual_values, expected_values)


# class DownloadCsvM2MFieldsIntTests(DownloadCsvM2MFieldsStrTests):
#     """Unit tests for testing downloaded csv many-to-many fields with int slug."""

#     m2m_selector = "many_tags_int"
#     m2m_target_field = "id"
