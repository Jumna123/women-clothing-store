from django.contrib import admin

from .models import User
from .models import EmailVerificationRequest

# Register your models here.

admin.site.register(User)
admin.site.register(EmailVerificationRequest)