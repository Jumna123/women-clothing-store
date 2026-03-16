from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST  
from decimal import Decimal
from django.utils import timezone

from apps.adminpanel.models import Category, Product, ProductImage, Collection
from apps.accounts.models import Address
from .models import Wishlist, Cart, Order, OrderItem


def home(request):
    from apps.adminpanel.models import Category, Collection, StoreSettings
    from django.db.models import Count

    categories = Category.objects.all()
    collections = Collection.objects.annotate(
        num_products=Count('products')
    ).filter(
        num_products__gt=0,
        is_active=True
    )

    store_settings = StoreSettings.get_settings()
    marquee_items = [item.strip() for item in store_settings.marquee_text.split('|')]

    return render(request, "user/home.html", {
        "categories": categories,
        "collections": collections,
        "marquee_items": marquee_items,
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
from apps.adminpanel.models import StoreSettings

@login_required(login_url='accounts:userlogin')
def checkout(request):
    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product").prefetch_related("product__images")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("home:cart_view")

    store_settings = StoreSettings.get_settings()

    subtotal = sum(item.total_price() for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost
    tax = subtotal * Decimal("0.05")
    total = subtotal + shipping + tax

    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        delivery = request.POST.get('delivery', 'standard')

        if not address_id:
            messages.error(request, "Please select a delivery address.", extra_tags='checkout')
            return redirect("home:checkout")

        if not Address.objects.filter(id=address_id, user=request.user).exists():
            messages.error(request, "Invalid address selected.", extra_tags='checkout')
            return redirect("home:checkout")

        request.session['checkout_address_id'] = address_id
        request.session['checkout_delivery'] = delivery
        return redirect('home:checkout_payment')

    return render(request, "user/checkout.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "addresses": addresses,
        "default_address": default_address,
        "store_settings": store_settings,
    })


@login_required(login_url='accounts:userlogin')
def checkout_payment(request):
    address_id = request.session.get('checkout_address_id')
    delivery = request.session.get('checkout_delivery', 'standard')

    if not address_id:
        messages.error(request, "Please complete your address first.", extra_tags='checkout')
        return redirect('home:checkout')

    address = get_object_or_404(Address, id=address_id, user=request.user)

    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product").prefetch_related("product__images")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("home:cart_view")

    store_settings = StoreSettings.get_settings()

    subtotal = sum(item.total_price() for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost
    if delivery == 'express':
        shipping += store_settings.express_shipping_cost
    tax = subtotal * Decimal("0.05")
    total = subtotal + shipping + tax

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')

        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            status="pending",
            payment_method=payment_method,
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
        request.session.pop('checkout_address_id', None)
        request.session.pop('checkout_delivery', None)

        messages.success(request, f"Order #{order.id} placed successfully!", extra_tags='checkout')
        return redirect('home:user_orders')

    return render(request, "user/payment.html", {
        "address": address,
        "delivery": delivery,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "store_settings": store_settings,
    })



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

def search_products(request):
    query = request.GET.get('q', '').strip()
    products = []

    if query:
        products = Product.objects.filter(
            is_available=True
        ).filter(
            Q(product_name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__category_name__icontains=query)
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        )

    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    else:
        wishlist_products = []

    return render(request, 'user/search_results.html', {
        'query': query,
        'products': products,
        'wishlist_products': wishlist_products,
    })


@login_required(login_url='accounts:userlogin')
@require_POST
def request_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.can_return:
        messages.error(request, "This order is not eligible for return.", extra_tags='checkout')
        return redirect('home:order_detail', order_id=order_id)

    reason = request.POST.get('return_reason', '').strip()
    if not reason:
        messages.error(request, "Please provide a reason for return.", extra_tags='checkout')
        return redirect('home:order_detail', order_id=order_id)

    order.status = 'return_requested'
    order.return_reason = reason
    order.return_requested_at = timezone.now()
    order.save()

    messages.success(request, "Return request submitted.", extra_tags='checkout')
    return redirect('home:order_detail', order_id=order_id)