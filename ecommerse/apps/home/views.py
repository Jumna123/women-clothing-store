from django.shortcuts import render,redirect, get_object_or_404
from django.db.models import Prefetch
from apps.adminpanel.models import Category, Product, ProductImage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist,Cart,Order
from apps.adminpanel.models import Product
from django.http import JsonResponse
from decimal import Decimal



def home(request):
    from apps.adminpanel.models import Category
    from apps.adminpanel.models import Collection
    categories = Category.objects.all()
    collections=Collection.objects.all()
    return render(request, "user/home.html", {
        "categories": categories,
        "collections":collections
    })



def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)

    products = Product.objects.filter(
        category=category,
        is_available=True
    ).prefetch_related(
        Prefetch(
            'images',
            queryset=ProductImage.objects.filter(is_primary=True)
        )
    )

    # 🔥 ADD THIS BLOCK
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    else:
        wishlist_products = []

    return render(request, "user/product_listingpage.html", {
        "category": category,
        "products": products,
        "wishlist_products": wishlist_products   # 👈 add this
    })



@login_required(login_url='accounts:userlogin')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        wishlist_item.delete()
        messages.info(
            request,
            f"Removed '{product.product_name}' from your wishlist."
        )
    else:
        messages.success(
            request,
            f"Added '{product.product_name}' to your wishlist."
        )

    return redirect(request.META.get('HTTP_REFERER') or 'home:index')

@login_required(login_url='accounts:userlogin')
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    # check if opened from profile
    from_profile = request.GET.get("from") == "profile"

    context = {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
        'from_profile': from_profile   # send to template
    }

    return render(request, 'user/wishlist.html', context)

    from .models import Cart

@login_required(login_url='accounts:userlogin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect(request.META.get('HTTP_REFERER') or 'home:cart_view')

@login_required(login_url='accounts:userlogin')
def cart_view(request):
    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related('product')

    # Calculate subtotal
    subtotal = sum(item.total_price() for item in cart_items)

    # Shipping logic
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < Decimal("1000"):
        shipping = Decimal("50")

    # Tax (5%)
    tax = subtotal * Decimal("0.05")

    # Final total
    total = subtotal + shipping + tax

    # Size handling
    for item in cart_items:
        if item.product.size:
            item.available_sizes = [
                s.strip() for s in item.product.size.split(",")
            ]
        else:
            item.available_sizes = []

    item_count = cart_items.count()

    return render(request, "user/cart.html", {
        "cart_items": cart_items,
        "item_count": item_count,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
    })
@login_required(login_url='accounts:userlogin')
def update_cart(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "increase":
            cart_item.quantity += 1

        elif action == "decrease":
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                cart_item.delete()
                return redirect('home:cart_view')

        cart_item.save()   
    return redirect('home:cart_view')


def get_product_sizes(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    sizes = []
    if product.size:
        sizes = [s.strip() for s in product.size.split(",")]

    return JsonResponse({
        "name": product.product_name,
        "price": product.price,
        "image": product.image.url,
        "sizes": sizes
    })

@login_required
def move_to_cart(request, product_id):
    if request.method == "POST":
        size = request.POST.get("size")

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product_id=product_id,
            defaults={
                "size": size,
                "quantity": 1
            }
        )

        # If already exists → increase quantity
        if not created:
            cart_item.quantity += 1
            cart_item.size = size  # optional: update size
            cart_item.save()

        # Remove from wishlist
        Wishlist.objects.filter(
            user=request.user,
            product_id=product_id
        ).delete()

    return redirect("home:wishlist_view")


def get_product_sizes(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    sizes = []
    if product.size:
        sizes = [s.strip() for s in product.size.split(",")]

    # FIX IMAGE FROM RELATED MODEL
    primary_image = product.images.first()
    image_url = primary_image.image.url if primary_image else "/static/images/no-image.png"

    return JsonResponse({
        "name": product.product_name,
        "price": product.price,
        "image": image_url,
        "sizes": sizes
    })

@login_required
def remove_cart_item(request, item_id):
    if request.method == "POST":
        Cart.objects.filter(
            id=item_id,
            user=request.user
        ).delete()

    return redirect("home:cart_view")

@login_required
def move_to_wishlist(request, item_id):
    if request.method == "POST":

        cart_item = Cart.objects.filter(
            id=item_id,
            user=request.user
        ).first()

        if not cart_item:
            return redirect("home:cart")  # avoid crash

        # Add to wishlist
        Wishlist.objects.get_or_create(
            user=request.user,
            product=cart_item.product
        )

        # Remove from cart
        cart_item.delete()

    return redirect("home:cart_view")

def product_detail(request, slug):

    product = Product.objects.get(slug=slug)

    images = product.images.all()
    sizes = product.size.split(",")


    return render(request, "user/product_view.html", {
        "product": product,
        "images": images,
        "sizes": sizes

    })



@login_required(login_url='accounts:userlogin')
def checkout(request):

    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product")


    # SUBTOTAL
    subtotal = sum(item.total_price() for item in cart_items)


    # SHIPPING
    shipping = Decimal("0")

    if subtotal > Decimal("0") and subtotal < Decimal("1000"):
        shipping = Decimal("50")


    # TAX (5%)
    tax = subtotal * Decimal("0.05")


    # TOTAL
    total = subtotal + shipping + tax


    context = {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total
    }


    return render(request, "user/checkout.html", context)

@login_required
def user_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "user/orders.html", {
        "orders": orders
    })


@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(request, "orders/order_detail.html", {
        "order": order
    }) 

