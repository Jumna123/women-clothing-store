from django.shortcuts import render,redirect, get_object_or_404
from django.db.models import Prefetch
from apps.adminpanel.models import Category, Product, ProductImage,Collection
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist, Cart, Order, OrderItem
from apps.adminpanel.models import Product
from django.http import JsonResponse
from decimal import Decimal
from apps.accounts.models import Address



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

def collection_products(request, pk):
    collection = get_object_or_404(Collection, pk=pk, is_active=True)

    products = Product.objects.filter(
        collections=collection,
        is_available=True
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )

    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    else:
        wishlist_products = []

    return render(request, "user/product_listingpage.html", {
        "category": collection,  # reuse same template
        "products": products,
        "wishlist_products": wishlist_products,
        "is_collection": True,
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



from apps.accounts.models import Address

@login_required(login_url='accounts:userlogin')
def checkout(request):
    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product").prefetch_related("product__images")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("home:cart_view")

    subtotal = sum(item.total_price() for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < Decimal("1000"):
        shipping = Decimal("50")
    tax = subtotal * Decimal("0.05")
    total = subtotal + shipping + tax

    # ✅ fetch saved addresses
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    default_address = addresses.filter(is_default=True).first()

    return render(request, "user/checkout.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "addresses": addresses,
        "default_address": default_address,
    })


@login_required(login_url='accounts:userlogin')
def place_order(request):
    if request.method != "POST":
        return redirect("home:checkout")

    cart_items = Cart.objects.filter(user=request.user).select_related("product")

    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("home:cart_view")

    address_id = request.POST.get("address_id")
    payment_method = request.POST.get("payment_method", "cod")

    # ✅ if no saved address selected, create one from form fields
    if not address_id:
        full_name = request.POST.get("new_full_name", "").strip()
        phone = request.POST.get("new_phone", "").strip()
        house_name = request.POST.get("new_house_name", "").strip()
        street = request.POST.get("new_street", "").strip()
        city = request.POST.get("new_city", "").strip()
        state = request.POST.get("new_state", "").strip()
        pincode = request.POST.get("new_pincode", "").strip()

        if not all([full_name, phone, house_name, street, city, state, pincode]):
            messages.error(request, "Please fill in all address fields.")
            return redirect("home:checkout")

        address = Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            house_name=house_name,
            street=street,
            city=city,
            state=state,
            pincode=pincode,
            is_default=not Address.objects.filter(user=request.user).exists()
        )
    else:
        address = get_object_or_404(Address, id=address_id, user=request.user)

    subtotal = sum(item.total_price() for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < Decimal("1000"):
        shipping = Decimal("50")
    tax = subtotal * Decimal("0.05")
    total = subtotal + shipping + tax

    order = Order.objects.create(
        user=request.user,
        total_amount=total,
        status="pending",
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.discount_price or item.product.price,
            size=item.size,
        )

    cart_items.delete()

    messages.success(request, f"Order #{order.id} placed successfully!")
    return redirect("home:user_orders")

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

