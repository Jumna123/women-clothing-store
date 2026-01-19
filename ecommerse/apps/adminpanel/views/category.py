from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..models import Category



def category(request):
    categories = Category.objects.all()

    return render(request, "adminpanel/category.html", {
        "categories": categories
    })

@login_required
def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get("category_name")
        category_image = request.FILES.get("category_image")
        is_active = request.POST.get("is_active") == "on"

        # validation
        if not category_name:
            messages.error(request, "Category name is required")
            return redirect("add_category")

        if Category.objects.filter(category_name__iexact=category_name).exists():
            messages.error(request, "Category already exists")
            return redirect("add_category")

        if not category_image:
            messages.error(request, "Category image is required")
            return redirect("add_category")

        Category.objects.create(
            category_name=category_name,
            category_image=category_image,
            is_active=is_active
        )

        messages.success(request, "Category added successfully")
        return redirect("add_category")

    return render(request, "admin/category/add_category.html")

