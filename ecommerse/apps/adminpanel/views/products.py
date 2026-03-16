from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Product, Category, ProductImage,Collection
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from ..forms import ProductForm


from django.core.paginator import Paginator

def product(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    stock_status = request.GET.get('stock', '')

    products = Product.objects.all().order_by('-created_at')

    if q:
        products = products.filter(product_name__icontains=q)

    if category_id:
        products = products.filter(category_id=category_id)

    if stock_status == 'in_stock':
        products = products.filter(is_available=True)
    elif stock_status == 'out_of_stock':
        products = products.filter(is_available=False)

    paginator = Paginator(products, 10)  # 10 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_active=True)

    return render(request, "adminpanel/products.html", {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "total_count": paginator.count,
    })


def addproduct(request):
    categories = Category.objects.all()
    collections = Collection.objects.filter(is_active=True)  # ✅ add this

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            images = request.FILES.getlist("images")
            if not images:
                messages.error(request, "Please upload at least one product image.")
                return render(request, "adminpanel/addproduct.html", {
                    "form": form,
                    "categories": categories,
                    "collections": collections,  # ✅
                    "is_edit": False
                })
            product = form.save(commit=False)
            if not product.is_available:
                product.stock_quantity = 0
            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")
            product.size = ",".join(request.POST.getlist("size"))
            product.save()

            # ✅ save selected collections (ManyToMany)
            selected_collections = request.POST.getlist("collections")
            if selected_collections:
                product.collections.set(selected_collections)
            else:
                product.collections.clear()

            for index, image in enumerate(images):
                ProductImage.objects.create(product=product, image=image, is_primary=(index == 0))
            messages.success(request, "Product added successfully")
            return redirect("adminpanel:product")
        else:
            messages.error(request, "Please fix the errors below")
    else:
        form = ProductForm()

    return render(request, "adminpanel/addproduct.html", {
        "form": form,
        "categories": categories,
        "collections": collections,  # ✅
        "is_edit": False
    })


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    collections = Collection.objects.filter(is_active=True)  # ✅ add this

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
                    "collections": collections,  # ✅
                    "is_edit": True
                })
            product = form.save(commit=False)
            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")
            product.size = ",".join(request.POST.getlist("size"))
            product.save()

            # ✅ save selected collections
            selected_collections = request.POST.getlist("collections")
            if selected_collections:
                product.collections.set(selected_collections)
            else:
                product.collections.clear()

            for index, image in enumerate(new_images):
                ProductImage.objects.create(product=product, image=image, is_primary=(index == 0 and not existing_images))
            messages.success(request, "Product updated successfully")
            return redirect("adminpanel:product")
        else:
            messages.error(request, "Please fix the errors below")
    else:
        form = ProductForm(instance=product)

    SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "One Size"]
    sizes = product.size.split(",") if product.size else []
    sizes = sorted(sizes, key=lambda x: SIZE_ORDER.index(x) if x in SIZE_ORDER else 999)

    return render(request, "adminpanel/addproduct.html", {
        "form": form,
        "product": product,
        "sizes": sizes,
        "collections": collections,  # ✅
        "is_edit": True
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


