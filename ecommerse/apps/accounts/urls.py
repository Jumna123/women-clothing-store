from django.urls import path
from .views.admin_auth import admin_login
from .views.user_auth import signup_view
from .views.user_auth import userlogin
from .views.user_auth import verify_email_view
from .views.user_auth import profile
from .views.user_auth import user_logout
from .views.user_auth import forgot_password
from .views.user_auth import reset_password


app_name='accounts'

urlpatterns = [
    path('',admin_login,name='admin_login'),
    path('signup/',signup_view,name='signup'),
    path('login/',userlogin,name='userlogin'),
    path('verify/', verify_email_view, name="verify_email"),
    path('profile/',profile,name='profile'),
    path("logout/", user_logout, name="logout"),
    path("forgot-password/",forgot_password, name="forgot_password"),
    path("forgot-password/reset/",reset_password, name="reset_password"),

]

