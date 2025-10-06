from pathlib import Path
from typing import ClassVar, Optional

from django.core.files import File
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe

from clubs.models import ClubScopedModel
from core.abstracts.models import ManagerBase, ModelBase
from utils.formatting import format_bytes
from utils.helpers import get_full_url
from utils.models import OneToOneOrNoneField, UploadFilepathFactory


class LinkManager(ManagerBase["Link"]):
    """Manage queries for Links."""

    def create(self, target_url: str, club, create_qrcode=False, **kwargs):
        link = super().create(target_url=target_url, club=club, **kwargs)

        if create_qrcode:
            QRCode.objects.create(link=link)

        return link


class Link(ClubScopedModel, ModelBase):
    """Track visits to target url."""

    club = models.ForeignKey(
        "clubs.Club", on_delete=models.CASCADE, related_name="links"
    )
    target_url = models.URLField(help_text="The final url we want to track clicks to.")
    display_name = models.CharField(null=True, blank=True)
    is_tracked = models.BooleanField(
        default=False, help_text="Should clicking this url create a `LinkVisit` object?"
    )

    # Relationships
    visits: models.QuerySet["LinkVisit"]
    qrcode: Optional["QRCode"] = None

    # Dynamic Properties
    @property
    def tracking_url_path(self) -> str:
        # Extended models use link_id
        return reverse("redirect-link", kwargs={"link_id": self.id or self.link_id})

    @property
    def tracking_url(self):
        return get_full_url(self.tracking_url_path)

    @property
    def url(self) -> str:
        """
        Primary url for the link.

        If `is_masked=True` will return a proxy url to this server,
        otherwise will return the target url.
        """
        return self.tracking_url if self.is_tracked else self.target_url

    @property
    def link_visits(self):
        return self.visits.aggregate(sum=models.Sum("amount")).get("sum", 0)

    def as_html(self, new_tab=True):
        if new_tab:
            return mark_safe(
                f'<a href="{self.tracking_url}" target="_blank">{self.tracking_url}</a>'
            )

        return mark_safe(f'<a href="{self.tracking_url}">{self.tracking_url}</a>')

    def generate_qrcode(self):
        """Create QRCode for link."""

        if self.qrcode is not None:
            return

        QRCode.objects.create(link=self)

    # Overrides
    objects: ClassVar[LinkManager] = LinkManager()

    def __str__(self):
        return self.display_name or self.tracking_url or super().__str__()


class LinkVisitManager(ManagerBase["LinkVisit"]):
    """Manage Link Visit queries."""

    def create(self, link: Link, ipaddress: str, **kwargs):
        return super().create(link=link, ipaddress=ipaddress, **kwargs)


class LinkVisit(ClubScopedModel, ModelBase):
    """Who visited a link."""

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="visits")
    # TODO: stash breadcrumb on browser to prevent VPNs from registering as multiple visits
    ipaddress = models.GenericIPAddressField(
        help_text="IP Address of the person that visited the link"
    )
    context = models.JSONField(
        null=True, blank=True, help_text="Extra meta information"
    )
    amount = models.IntegerField(
        default=0, help_text="Number of times this person clicked the link"
    )

    # Overrides
    objects: ClassVar[LinkVisitManager] = LinkVisitManager()

    @property
    def clubs(self):
        return self.link.clubs

    def __str__(self):
        return super().__str__()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("link", "ipaddress"),
                name="unique_ip_per_link",
            ),
        )

    # Methods
    def increment(self, by: int = 1, commit=True):
        """Increase visit amount."""

        self.amount += by

        if commit:
            self.save()


class QRCode(ClubScopedModel, ModelBase):
    """Store image for QR Codes."""

    qrcode_upload_path = UploadFilepathFactory("clubs/qrcodes/")

    link = OneToOneOrNoneField(
        Link, on_delete=models.CASCADE, related_name="qrcode", primary_key=True
    )
    image = models.ImageField(null=True, blank=True, upload_to=qrcode_upload_path)

    def save_image(self, filepath: str):
        """Takes path for image and sets it to the image field."""

        path = Path(filepath)

        with path.open(mode="rb") as f:
            self.image = File(f, name=f.name)
            self.save()

    # Dynamic Properties
    @property
    def url(self) -> str:
        return self.link.tracking_url

    @property
    def width(self) -> int:
        if self.image:
            return self.image.width

    @property
    def download_url(self) -> str:
        return get_full_url(reverse("analytics:download_qrcode", args=[self.pk]))

    @property
    def size(self) -> str:
        if self.image:
            return format_bytes(self.image.size)

    # Overrides
    @property
    def clubs(self):
        return self.link.clubs

    def __str__(self) -> str:
        return f'QRCode for "{self.link}"'

    class Meta:
        verbose_name = "QR Code"
