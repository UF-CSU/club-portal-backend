from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("health/", views.health_check, name="health"),
    path("admin/sysinfo/", views.sys_info, name="sysinfo"),
]
