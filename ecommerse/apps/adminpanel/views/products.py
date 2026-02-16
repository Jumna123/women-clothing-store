from django.shortcuts import render, redirect
from django.contrib import messages
from ..models import Product, Category, ProductImage


def product(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, "adminpanel/products.html", {
        "products": products
    })


def addproduct(request):
    categories = Category.objects.all()

    if request.method == "POST":
        # ---------- READ FORM DATA ----------
        product_name = request.POST.get("product_name")
        
        price = request.POST.get("price")
        discount_price = request.POST.get("discount_price")
        description = request.POST.get("description")
        colour = request.POST.get("colour")
        sizes = request.POST.getlist("size")
        stock_quantity = request.POST.get("stock_quantity")
        is_available = request.POST.get("is_available")
        category_id = request.POST.get("category")
        

        # ---------- BASIC VALIDATION ----------
        if not product_name or not price or not category_id:
            messages.error(request, "Required fields are missing")
            return redirect("adminpanel:addproduct")

        # ---------- STOCK LOGIC ----------
        if is_available:
            stock_quantity = int(stock_quantity) if stock_quantity else 0
        else:
            stock_quantity = 0
            is_available = False

        # ---------- DISCOUNT VALIDATION ----------
        if discount_price:
            if float(discount_price) >= float(price):
                messages.error(request, "Discount price must be less than price")
                return redirect("addproduct")
        else:
            discount_price = None

        # ---------- SIZE LOGIC (✅ CORRECT PLACE) ----------
        size_string = ",".join(sizes)

        # ---------- CREATE PRODUCT ----------
        product = Product.objects.create(
            product_name=product_name,
            
            price=price,
            discount_price=discount_price,
            description=description,
            colour=colour,
            size=size_string,            # ✅ FIXED
            stock_quantity=stock_quantity,
            is_available=bool(is_available),
            category_id=category_id,
        )
        print('Test')

        # ---------- MULTIPLE IMAGES ----------
        images = request.FILES.getlist("images")
        print(request.FILES)
        print(images)
        for index, image in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(index == 0)
            )

        messages.success(request, "Product added successfully")
        return redirect("adminpanel:product")

    return render(request, "adminpanel/addproduct.html", {
        "categories": categories
    })


