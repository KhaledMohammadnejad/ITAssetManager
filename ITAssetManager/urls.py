
"""
URL configuration for ITAssetManager project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from core import views


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "reports/",
        views.reports,
        name="reports"
    ),

    path(
        "locations/",
        views.location_management,
        name="location_management",
    ),

    path(
        "locations/add/",
        views.location_create,
        name="location_create",
    ),

    path(
        "login/",
        views.RequesterLoginView.as_view(),
        name="login"
    ),

    path(
        "logout/",
        LogoutView.as_view(next_page="login"),
        name="logout",
    ),

    path(
        "requester/",
        views.requester_page,
        name="requester"
    ),

    path(
        "requests/",
        views.request_list,
        name="request_list"
    ),

    path(
        "requests/<int:pk>/",
        views.request_detail,
        name="request_detail"
    ),
]

