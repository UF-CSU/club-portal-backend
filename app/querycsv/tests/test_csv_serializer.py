from querycsv.tests.utils import CsvDataTestsBase


class CsvSerializerTests(CsvDataTestsBase):
    """Unit tests for csv serializer."""

    def test_csv_template_all_fields(self):
        """A csv template should have all flat fields."""

        file = self.service.get_csv_template("all")
        df = self.csv_to_df(file)
        fields = list(df.columns)

        expected_fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "unique_name",
            "one_tag_str",
            "many_tags_str",
            "many_tags_int",
            "one_tag_nested.id",
            "one_tag_nested.name",
            "one_tag_nested.color",
            "many_tags_nested[n].id",
            "many_tags_nested[n].name",
            "many_tags_nested[n].color",
        ]

        for expected_field in expected_fields:
            self.assertIn(expected_field, fields)

    def test_csv_template_required_fields(self):
        """A csv template should have required flat fields."""

        file = self.service.get_csv_template("required")
        df = self.csv_to_df(file)
        fields = list(df.columns)

        expected_fields = ["name"]

        for expected_field in expected_fields:
            self.assertIn(expected_field, fields)

    def test_csv_template_writable_fields(self):
        """A csv template should have writable flat fields."""

        file = self.service.get_csv_template("writable")
        df = self.csv_to_df(file)
        fields = list(df.columns)

        expected_fields = [
            "name",
            "unique_name",
            "one_tag_str",
            "many_tags_str",
            "many_tags_int",
            "one_tag_nested.name",
            "one_tag_nested.color",
            "many_tags_nested[n].name",
            "many_tags_nested[n].color",
        ]

        for expected_field in expected_fields:
            self.assertIn(expected_field, fields)
