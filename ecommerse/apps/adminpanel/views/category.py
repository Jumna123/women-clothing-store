# adminpanel/views/category.py — FINAL CLEAN VERSION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.views.decorators.http import require_POST
from ..models import Category
from ..forms import CategoryForm


def category(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    categories = Category.objects.annotate(product_count=Count('products'))

    if q:
        categories = categories.filter(category_name__icontains=q)
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)

    return render(request, "adminpanel/category.html", {"categories": categories})


@login_required
def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get("category_name")
        category_image = request.FILES.get("category_image")
        is_active = bool(request.POST.get("is_active"))

        if not category_name:
            messages.error(request, "Category name is required")
            return redirect("adminpanel:category")
        if Category.objects.filter(category_name__iexact=category_name).exists():
            messages.error(request, "Category already exists")
            return redirect("adminpanel:category")
        if not category_image:
            messages.error(request, "Category image is required")
            return redirect("adminpanel:category")

        Category.objects.create(
            category_name=category_name,
            category_image=category_image,
            is_active=is_active
        )
        messages.success(request, "Category added successfully")
        return redirect("adminpanel:category")

    return render(request, "adminpanel/add_category.html")


def category_toggle_status(request, pk):
    if request.method == "POST":
        category = get_object_or_404(Category, pk=pk)
        category.is_active = not category.is_active
        category.save()
        messages.success(request, "Category activated" if category.is_active else "Category deactivated")
    return redirect("adminpanel:category")


@require_POST
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect("adminpanel:category")


def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("adminpanel:category")
    else:
        form = CategoryForm(instance=category)

    return render(request, "adminpanel/add_category.html", {
        "form": form,
        "category": category
    })