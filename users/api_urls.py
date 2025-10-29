from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import api_views

# Main router
router = DefaultRouter()
router.register(r"users", api_views.UserViewSet, basename="user")
router.register(r"roles", api_views.RoleViewSet, basename="role")
router.register(r"permissions", api_views.PermissionViewSet, basename="permission")
router.register(r"access-tokens", api_views.AccessTokenViewSet, basename="access-token")

# Nested routers for user relationships
# users_router = routers.NestedDefaultRouter(router, r"users", lookup="user")
# users_router.register(r"roles", api_views.UserRoleViewSet, basename="user-roles")
# users_router.register(
#     r"tokens", api_views.UserAccessTokenViewSet, basename="user-tokens"
# )

# Roles nested router
# roles_router = routers.NestedDefaultRouter(router, r"roles", lookup="role")
# roles_router.register(
#     r"permissions", api_views.RolePermissionViewSet, basename="role-permissions"
# )

urlpatterns = [
    path("", include(router.urls)),
    # path("", include(users_router.urls)),
    # path("", include(roles_router.urls)),
    # Additional endpoints
    path("auth/login/", api_views.LoginAPIView.as_view(), name="auth-login"),
    path("auth/logout/", api_views.LogoutAPIView.as_view(), name="auth-logout"),
    path("auth/me/", api_views.CurrentUserAPIView.as_view(), name="auth-me"),
    path(
        "auth/change-password/",
        api_views.ChangePasswordAPIView.as_view(),
        name="auth-change-password",
    ),
    # Bulk operations
    path(
        "users/bulk-assign-role/",
        api_views.BulkAssignRoleAPIView.as_view(),
        name="bulk-assign-role",
    ),
    path(
        "users/bulk-revoke-role/",
        api_views.BulkRevokeRoleAPIView.as_view(),
        name="bulk-revoke-role",
    ),
    path(
        "roles/bulk-assign-permission/",
        api_views.BulkAssignPermissionAPIView.as_view(),
        name="bulk-assign-permission",
    ),
    # Statistics
    path("stats/users/", api_views.UserStatsAPIView.as_view(), name="user-stats"),
    path("stats/roles/", api_views.RoleStatsAPIView.as_view(), name="role-stats"),
]
