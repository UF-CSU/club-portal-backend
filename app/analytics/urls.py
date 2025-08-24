from django.urls import path

from analytics import views

app_name = "analytics"

urlpatterns = [
    path("qrcode/<int:id>/", views.download_qrcode_view, name="download_qrcode")
]
