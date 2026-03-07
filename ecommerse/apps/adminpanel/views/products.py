from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Product, Category, ProductImage
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from ..forms import ProductForm


def product(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, "adminpanel/products.html", {
        "products": products
    })


def addproduct(request):
    categories = Category.objects.all()

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            images = request.FILES.getlist("images")

            if not images:
                messages.error(request, "Please upload at least one product image.")
                return render(request, "adminpanel/addproduct.html", {
                    "form": form,
                    "categories": categories,
                    "is_edit": False,
                })

            product = form.save(commit=False)  # ✅ only once

            if not product.is_available:
                product.stock_quantity = 0


            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")
            product.size = ",".join(request.POST.getlist("size"))

            product.save()

            for index, image in enumerate(images):  # ✅ reuse already fetched list
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(index == 0)
                )

            messages.success(request, "Product added successfully")
            return redirect("adminpanel:product")
        else:
            messages.error(request, "Please fix the errors below")
    else:
        form = ProductForm()

    return render(request, "adminpanel/addproduct.html", {
        "form": form,
        "categories": categories,
        "is_edit": False,
    })


@require_POST
def delete_product_image(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    image.delete()
    return JsonResponse({"success": True})  # ✅ moved import to top


@require_POST
def delete_Product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("adminpanel:product")


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            new_images = request.FILES.getlist("images")
            existing_images = product.images.exists()

            if not new_images and not existing_images:
                messages.error(request, "Please upload at least one product image.")
                return render(request, "adminpanel/addproduct.html", {
                    "form": form,
                    "product": product,
                    "is_edit": True,
                })

            product = form.save(commit=False)

            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")

            if product.discount_price and product.discount_price >= product.price:
                messages.error(request, "Discount price must be less than the original price")
                return redirect("adminpanel:edit_product", pk=pk)

            product.size = ",".join(request.POST.getlist("size"))
            product.save()

            for index, image in enumerate(new_images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(index == 0 and not existing_images)
                )

            messages.success(request, "Product updated successfully")
            return redirect("adminpanel:product")
        else:
            messages.error(request, "Please fix the errors below")
            print("Form errors:", form.errors)

    else:
        form = ProductForm(instance=product)

    SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "One Size"]
    sizes = product.size.split(",") if product.size else []
    sizes = sorted(sizes, key=lambda x: SIZE_ORDER.index(x) if x in SIZE_ORDER else 999)

    return render(request, "adminpanel/addproduct.html", {
        "form": form,
        "product": product,
        "sizes": sizes,
        "is_edit": True,
    })