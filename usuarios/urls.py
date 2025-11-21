from django.contrib import admin
from django.urls import path
from .views import (
    CustomUserListView,
    CustomUserRetrieveUpdateDestroyView,
    AssignRoleView,
    RemoveRoleView,
    VerifyEmailView,
    UserProfileUpdateView,
    CustomUserRegisterView,
    CustomUserLoginView,
    ChangePasswordView,
    DocumentTypeListView,
)
from usuarios.password_reset import PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    # Users Auth
    path('users/register/', CustomUserRegisterView.as_view(), name='user-register'),
    path('users/login/', CustomUserLoginView.as_view(), name='user-login'),
    path('users/change-password/', ChangePasswordView.as_view(), name='user-change-password'),
    # Users CRUD
    path('users/', CustomUserListView.as_view(), name="user-list"),
    path('users/<int:pk>/', CustomUserRetrieveUpdateDestroyView.as_view(), name="user-detail"),
    path('users/<int:pk>/assign-role/', AssignRoleView.as_view(), name='user-assign-role'),
    path('users/<int:pk>/remove-role/', RemoveRoleView.as_view(), name='user-remove-role'),
    path('users/verify-email/', VerifyEmailView.as_view(), name='user-verify-email'),
    # Password Reset
    path('users/password-reset/', PasswordResetRequestView.as_view(), name='user-password-reset'),
    path('users/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='user-password-reset-confirm'),

    # Endpoint para edición de perfil propio
    path('users/profile/', UserProfileUpdateView.as_view(), name='user-profile-update'),
    
    # Document Types
    path('document-types/', DocumentTypeListView.as_view(), name='document-type-list'),
]

