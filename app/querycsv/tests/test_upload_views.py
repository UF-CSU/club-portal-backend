import pandas as pd
from django.template.response import TemplateResponse
from django.test import RequestFactory
from rest_framework import status

from core.mock.models import Buster
from core.mock.serializers import BusterCsvSerializer
from querycsv.forms import CsvHeaderMappingFormSet, CsvUploadForm
from querycsv.models import QueryCsvUploadJob
from querycsv.tests.test_upload_data import UploadCsvTestsBase
from querycsv.views import QueryCsvViewSet


class UploadCsvViewsTests(UploadCsvTestsBase):
    """Test functionality for upload views used in admin."""

    model_class = Buster
    serializer_class = BusterCsvSerializer

    def get_reverse(self, name="fallback"):
        return "core:index"

    def setUp(self):
        self.views = QueryCsvViewSet(
            self.serializer_class, get_reverse=self.get_reverse
        )
        self.req_factory = RequestFactory()

        return super().setUp()

    ####################
    # == Unit Tests == #
    ####################

    def test_upload_csv(self):
        """Should show form for uploading csv."""

        req = self.req_factory.get("/")
        res: TemplateResponse = self.views.upload_csv(request=req)

        self.assertIsInstance(res, TemplateResponse)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check context
        self.assertIsInstance(res.context_data["form"], CsvUploadForm)
        self.assertEqual(
            res.context_data["template_url"], self.get_reverse("csv_template")
        )
        # FIXME: Checking csv fields in context failes
        # self.assertEqual(
        #     res.context_data["all_fields"], self.service.flat_fields.values()
        # )
        self.assertEqual(
            res.context_data["unique_together_fields"],
            self.serializer.unique_together_fields,
        )

    def test_map_upload_csv_headers_get(self):
        """Should show form for header associations."""

        self.initialize_csv_data()
        job = QueryCsvUploadJob.objects.create(
            serializer_class=self.serializer_class, filepath=self.filepath
        )

        req = self.req_factory.get("/")
        res: TemplateResponse = self.views.map_upload_csv_headers(
            request=req, id=job.id
        )
        self.assertIsInstance(res, TemplateResponse)

        # Check context
        context = res.context_data
        self.assertEqual(context["upload_job"], job)
        self.assertEqual(context["model_class_name"], job.model_class.__name__)
        self.assertIsInstance(context["formset"], CsvHeaderMappingFormSet)

    def test_map_upload_csv_headers_post(self):
        """Should add custom header associations for upload job."""

        # Initialize data
        self.initialize_csv_data()
        df = pd.read_csv(self.filepath)
        df.rename(columns={"name": "Test Name"}, inplace=True)
        self.df_to_csv(df, self.filepath)

        job = QueryCsvUploadJob.objects.create(
            serializer_class=self.serializer_class, filepath=self.filepath
        )
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-csv_header": "Test Name",
            "form-0-object_field": "name",
        }

        # Send request
        req = self.req_factory.post("/", data=data)
        res = self.views.map_upload_csv_headers(request=req, id=job.id)

        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        # Check mappings
        job.refresh_from_db()
        self.assertEqual(len(job.custom_fields), 1)

        self.assertEqual(job.custom_fields[0]["column_name"], "Test Name")
        self.assertEqual(job.custom_fields[0]["field_name"], "name")
