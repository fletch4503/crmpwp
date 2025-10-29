from django.urls import path
from . import views

app_name = "contacts"

urlpatterns = [
    # Основные страницы контактов
    path("", views.ContactListView.as_view(), name="contact_list"),
    path("create/", views.ContactCreateView.as_view(), name="contact_create"),
    path("<uuid:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("<uuid:pk>/update/", views.ContactUpdateView.as_view(), name="contact_update"),
    path("<uuid:pk>/delete/", views.ContactDeleteView.as_view(), name="contact_delete"),
    # Группы контактов
    path("groups/", views.ContactGroupListView.as_view(), name="group_list"),
    path("groups/create/", views.ContactGroupCreateView.as_view(), name="group_create"),
    path(
        "groups/<uuid:pk>/update/",
        views.ContactGroupUpdateView.as_view(),
        name="group_update",
    ),
    path(
        "groups/<uuid:pk>/delete/",
        views.ContactGroupDeleteView.as_view(),
        name="group_delete",
    ),
    # API endpoints
    path("api/", views.ContactAPIView.as_view(), name="api_contacts"),
    path(
        "api/<uuid:contact_id>/",
        views.ContactDetailAPIView.as_view(),
        name="api_contact_detail",
    ),
    # AJAX endpoints
    path("ajax/search/", views.contact_search_ajax, name="contact_search_ajax"),
    path(
        "ajax/<uuid:contact_id>/toggle-favorite/",
        views.toggle_favorite_ajax,
        name="toggle_favorite_ajax",
    ),
    path(
        "ajax/<uuid:contact_id>/add-interaction/",
        views.add_interaction_ajax,
        name="add_interaction_ajax",
    ),
    path(
        "ajax/add-to-group/",
        views.add_contact_to_group_ajax,
        name="add_contact_to_group_ajax",
    ),
]
