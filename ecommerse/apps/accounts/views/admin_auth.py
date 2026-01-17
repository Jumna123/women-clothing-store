from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_staff:
                login(request, user)
                return redirect("adminpanel:dashboard")
            else:
                messages.error(request, "You are not authorized as admin")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "accounts/admin_login.html")

