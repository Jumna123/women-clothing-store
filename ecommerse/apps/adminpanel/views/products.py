from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from ..models import Product, Category, ProductImage
from ..models import Product
from django.views.decorators.http import require_POST
from ..forms import ProductForm


def product(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, "adminpanel/products.html", {
        "products": products
    })


def addproduct(request):
    categories = Category.objects.all()

    if request.method == "POST":
        form = ProductForm(request.POST)

        if form.is_valid():
            product = form.save(commit=False)

            # custom logic
            if not product.is_available:
                product.stock_quantity = 0

            if product.discount_price and product.discount_price >= product.price:
                messages.error(request, "Discount price must be less than price")
                return redirect("adminpanel:addproduct")

            product.save()

            # handle multiple images
            images = request.FILES.getlist("images")
            for index, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(index == 0)
                )

            messages.success(request, "Product added successfully")
            return redirect("adminpanel:product")
    else:
        form = ProductForm()

    return render(
        request,
        "adminpanel/addproduct.html",
        {
            "form": form,
            "categories": categories,
            "is_edit": False,
        }
    )



@require_POST
def delete_Product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("adminpanel:product")

def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            product = form.save(commit=False)
            product.save()

            images = request.FILES.getlist("images")
            for image in images:
                ProductImage.objects.create(product=product, image=image)

            messages.success(request, "Product updated successfully")
            return redirect("adminpanel:product")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "adminpanel/addproduct.html",  
        {
            "form": form,
            "is_edit": True,
            "product": product,
        }
    )




