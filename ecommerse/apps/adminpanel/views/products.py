from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Product, Category, ProductImage, Collection, ProductSize
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

    paginator = Paginator(products, 10)
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
    collections = Collection.objects.filter(is_active=True)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            images = request.FILES.getlist("images")
            if not images:
                messages.error(request, "Please upload at least one product image.")
                return render(request, "adminpanel/addproduct.html", {
                    "form": form,
                    "categories": categories,
                    "collections": collections,
                    "is_edit": False
                })

            product = form.save(commit=False)
            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")
            product.is_trending = bool(request.POST.get("is_trending"))
            product.tags = request.POST.get("tags", "").strip()

            # ✅ Derive is_available and stock_quantity from size stocks
            size_names = request.POST.getlist('size_name')
            size_stocks = request.POST.getlist('size_stock')
            total_stock = sum(
                int(s) for s in size_stocks if s.isdigit()
            )
            product.stock_quantity = total_stock
            product.is_available = total_stock > 0

            # Store size names as comma-separated (keeps your existing field intact)
            product.size = ",".join(n for n in size_names if n)

            product.save()

            # ✅ Save per-size stock records
            for name, stock in zip(size_names, size_stocks):
                if name:
                    ProductSize.objects.create(
                        product=product,
                        size=name,
                        stock_quantity=int(stock) if stock.isdigit() else 0
                    )

            selected_collections = request.POST.getlist("collections")
            product.collections.set(selected_collections) if selected_collections else product.collections.clear()

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
        "collections": collections,
        "is_edit": False
    })


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    collections = Collection.objects.filter(is_active=True)

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
                    "collections": collections,
                    "is_edit": True,
                    "sizes": product.size.split(",") if product.size else [],
                })

            product = form.save(commit=False)
            product.color_hex = request.POST.get("color_hex")
            product.color_name = request.POST.get("color_name")
            product.is_trending = bool(request.POST.get("is_trending"))
            product.tags = request.POST.get("tags", "").strip()

            # ✅ Clear old size records and rebuild from POST data
            product.product_sizes.all().delete()

            size_names = request.POST.getlist('size_name')
            size_stocks = request.POST.getlist('size_stock')
            total_stock = sum(
                int(s) for s in size_stocks if s.isdigit()
            )
            product.stock_quantity = total_stock
            product.is_available = total_stock > 0
            product.size = ",".join(n for n in size_names if n)

            product.save()

            # ✅ Save updated per-size stock records
            for name, stock in zip(size_names, size_stocks):
                if name:
                    ProductSize.objects.create(
                        product=product,
                        size=name,
                        stock_quantity=int(stock) if stock.isdigit() else 0
                    )

            selected_collections = request.POST.getlist("collections")
            product.collections.set(selected_collections) if selected_collections else product.collections.clear()

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

    else:
        form = ProductForm(instance=product)

    SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "One Size"]
    sizes = product.size.split(",") if product.size else []
    sizes = sorted(sizes, key=lambda x: SIZE_ORDER.index(x) if x in SIZE_ORDER else 999)

    # ✅ Pass existing per-size stock data to the template for pre-filling
    existing_size_stocks = {
        ps.size: ps.stock_quantity
        for ps in product.product_sizes.all()
    }

    return render(request, "adminpanel/addproduct.html", {
        "form": form,
        "product": product,
        "sizes": sizes,
        "collections": collections,
        "is_edit": True,
        "product_tags": product.tags if product.tags else "",
        "existing_size_stocks": existing_size_stocks,  # ✅ for pre-filling stock inputs
    })


@require_POST
def delete_product_image(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    image.delete()
    return JsonResponse({"success": True})


@require_POST
def delete_Product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("adminpanel:product")