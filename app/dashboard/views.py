from django.shortcuts import render

# Create your views here.


def index(request):
    context = {}

    return render(request, "dashboard/dashboard_base.html", context)
