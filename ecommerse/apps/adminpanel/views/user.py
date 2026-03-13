from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

User = get_user_model()

def user_management(request):
    queryset = User.objects.filter(is_superuser=False).order_by("-date_joined")

    # Search — reads ?q= from URL
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(email__icontains=q)      |
            Q(username__icontains=q)
        )

    # Filter — reads ?filter= from URL
    status_filter = request.GET.get('filter', '')
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'blocked':
        queryset = queryset.filter(is_active=False)

    total_users = queryset.count()

    # Paginate — 10 per page
    paginator = Paginator(queryset, 10)
    users = paginator.get_page(request.GET.get('page', 1))

    return render(request, "adminpanel/user.html", {
        "users": users,
        "total_users": total_users,
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