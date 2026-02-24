from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "password-change/", views.PasswordChangeView.as_view(), name="password_change"
    ),
    path(
        "password-change/done/",
        views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    # Profile
    path("profile/", views.profile_view, name="profile"),
    path("profile/update/", views.profile_update, name="profile_update"),
    path("profile/email/change/", views.email_change, name="email_change"),
    path("profile/delete/", views.delete_account, name="delete_account"),
]
