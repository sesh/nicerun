"""nicerun URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse

from core.views import home


def robots(request):
    return HttpResponse("User-Agent: *", headers={"Content-Type": "text/plain; charset=UTF-8"})


def security(request):
    return HttpResponse(
        "Contact: <your-email>\nExpires: 2025-01-01T00:00:00.000Z",
        headers={"Content-Type": "text/plain; charset=UTF-8"},
    )


def privacy(request):
    return render(request, 'privacy.html')


def trigger_error(request):
    division_by_zero = 1 / 0
    return division_by_zero


urlpatterns = [
    path("", home),
    path("privacy/", privacy),

    # .well-known
    path("robots.txt", robots),
    path(".well-known/security.txt", security),
    path(".well-known/500", trigger_error),
    path("admin/", admin.site.urls),
]
