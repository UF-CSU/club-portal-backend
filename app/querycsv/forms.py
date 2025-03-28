from django import forms

from querycsv.consts import EXTRA_QUERYCSV_FIELDS
from querycsv.models import QueryCsvUploadJob


class CsvUploadForm(forms.Form):
    """Form used to upload csv and create/update objects."""

    file = forms.FileField(
        label="Select CSV or Excel Spreadsheet to upload.",
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )


class CsvHeaderMappingForm(forms.Form):
    """Map csv headers to object fields."""

    csv_header = forms.CharField(
        # disabled=True,
        required=True,
        widget=forms.TextInput(attrs={"readonly": True, "class": "form-control"}),
    )
    object_field = forms.ChoiceField(
        choices=[], required=True, widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, available_fields: list[str], **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["object_field"].choices = [
            (field, field.upper()) for field in EXTRA_QUERYCSV_FIELDS
        ] + [(field, field) for field in available_fields]


class CsvHeaderMappingFormSet(forms.formset_factory(CsvHeaderMappingForm, extra=0)):
    """Custom FormSet for defining csv header mappings."""

    def __init__(self, *args, upload_job: QueryCsvUploadJob, **kwargs):
        kwargs["form_kwargs"] = {
            **kwargs.get("form_kwargs", {}),
            "available_fields": upload_job.serializer_class().get_flat_fields().keys(),
        }

        super().__init__(*args, **kwargs)
