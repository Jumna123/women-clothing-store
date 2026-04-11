from functools import wraps
from django.shortcuts import redirect

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('adminpanel:admin_login')
        if not request.user.is_staff:
            return redirect('adminpanel:admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper