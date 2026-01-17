from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages



@login_required

def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request,'only admin can access')
        return redirect('accounts:admin_login')
    return render(request, 'adminpanel/dashboard.html')
