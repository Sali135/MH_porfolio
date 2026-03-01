from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard_home, name="dashboard_home"),
    path("dashboard/projects/", views.dashboard_project_list, name="dashboard_projects"),
    path(
        "dashboard/projects/create/",
        views.dashboard_project_create,
        name="dashboard_project_create",
    ),
    path(
        "dashboard/projects/<int:project_id>/edit/",
        views.dashboard_project_update,
        name="dashboard_project_update",
    ),
    path(
        "dashboard/projects/<int:project_id>/delete/",
        views.dashboard_project_delete,
        name="dashboard_project_delete",
    ),
    path("contact/", views.contact, name="contact"),
    path("contact/inbox/", views.contact_inbox, name="contact_inbox"),
    path("contact/inbox/export/", views.contact_inbox_export, name="contact_inbox_export"),
    path(
        "contact/inbox/<int:message_id>/",
        views.contact_inbox_update,
        name="contact_inbox_update",
    ),
]
