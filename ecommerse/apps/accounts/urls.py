from django.urls import path
from .views.admin_auth import admin_login
from .views.user_auth import (
    signup_view, userlogin, verify_email_view, profile,
    user_logout, forgot_password, reset_password,
    address_list, add_address, edit_address,
    delete_address, set_default_address
)
app_name="accounts"

urlpatterns = [
    path('', admin_login, name='admin_login'),
    path('signup/', signup_view, name='signup'),
    path('login/', userlogin, name='userlogin'),
    path('verify/', verify_email_view, name="verify_email"),
    path('profile/', profile, name='profile'),
    path("logout/", user_logout, name="logout"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("forgot-password/reset/", reset_password, name="reset_password"),

    # ✅ address URLs
    path("addresses/", address_list, name="address_list"),
    path("addresses/add/", add_address, name="add_address"),
    path("addresses/edit/<int:pk>/", edit_address, name="edit_address"),
    path("addresses/delete/<int:pk>/", delete_address, name="delete_address"),
    path("addresses/set-default/<int:pk>/", set_default_address, name="set_default_address"),
]

