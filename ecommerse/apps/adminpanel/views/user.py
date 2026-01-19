from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

def user_management(request):
    users = User.objects.all().order_by("-date_joined")
    return render(request, "adminpanel/user.html", {
        "users": users
    })

def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    return redirect("adminpanel:users")

def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    return redirect("adminpanel:users")
