from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST  
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta

from apps.adminpanel.models import Category, Product, ProductImage, Collection
from apps.adminpanel.models import Category, Product, ProductImage, Collection, ProductSize
from apps.accounts.models import Address
from .models import Wishlist, Cart, Order, OrderItem, ReturnRequest

def home(request):
    from apps.adminpanel.models import Category, Collection, StoreSettings
    from django.db.models import Count

    categories = Category.objects.filter(is_active=True)
    collections = Collection.objects.annotate(
        num_products=Count('products')
    ).filter(num_products__gt=0, is_active=True)

    trending_products = Product.objects.filter(
        is_trending=True,
        is_available=True
    ).prefetch_related('images')[:8]

    store_settings = StoreSettings.get_settings()
    marquee_items = [item.strip() for item in store_settings.marquee_text.split('|')]

    return render(request, "user/home.html", {
        "categories": categories,
        "collections": collections,
        "marquee_items": marquee_items,
        "trending_products": trending_products,
    })

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)

    products = Product.objects.filter(
        category=category
    ).prefetch_related('images')

    availability = request.GET.get('availability', '')
    if availability == 'in_stock':
        products = products.filter(is_available=True, stock_quantity__gt=0)
    elif availability == 'sold_out':
        products = products.filter(stock_quantity=0)

    sort = request.GET.get('sort', '')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')

    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    else:
        wishlist_products = []

    return render(request, "user/product_listingpage.html", {
        "category": category,
        "products": products,
        "wishlist_products": wishlist_products,
        "is_collection": False,
        "current_availability": availability,
        "current_sort": sort,
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
        "category": collection,
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
        messages.info(request, f"Removed '{product.product_name}' from your wishlist.")
    else:
        messages.success(request, f"Added '{product.product_name}' to your wishlist.")

    return redirect(request.META.get('HTTP_REFERER') or 'home:index')

@login_required(login_url='accounts:userlogin')
def wishlist_view(request):
    from apps.adminpanel.models import Category

    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    from_profile = request.GET.get("from") == "profile"
    categories = Category.objects.filter(is_active=True)

    return render(request, 'user/wishlist.html', {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
        'from_profile': from_profile,
        'categories': categories,
    })

@login_required(login_url='accounts:userlogin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.GET.get('size', '')
    quantity_to_add = int(request.GET.get('quantity', 1))

    product_size = ProductSize.objects.filter(product=product, size=size).first()

    if product_size:
        available_stock = product_size.stock_quantity
    else:
        available_stock = product.stock_quantity

    if available_stock <= 0:
        messages.error(request, f"'{product.product_name}' in size {size} is out of stock.")
        return redirect(request.META.get('HTTP_REFERER') or 'home:cart_view')

    cart_item, created = Cart.objects.get_or_create(
        user=request.user, product=product, size=size
    )

    if not created:
        new_qty = cart_item.quantity + quantity_to_add
        if new_qty > available_stock:
            messages.error(request, f"Only {available_stock} available in size {size}.")
            return redirect(request.META.get('HTTP_REFERER') or 'home:cart_view')
        cart_item.quantity = new_qty
    else:
        cart_item.quantity = min(quantity_to_add, available_stock)

    cart_item.save()
    messages.success(request, f"Added '{product.product_name}' (Size: {size}) to your bag.")
    return redirect(request.META.get('HTTP_REFERER') or 'home:cart_view')

@login_required(login_url='accounts:userlogin')
def cart_view(request):
    from apps.adminpanel.models import StoreSettings, PromoCode

    store_settings = StoreSettings.get_settings()
    cart_items = Cart.objects.filter(user=request.user).select_related('product')

    for item in cart_items:
        item.available_sizes = list(
            ProductSize.objects.filter(product=item.product).values_list('size', flat=True)
        )
        if item.product.discount_price and item.product.price:
            item.product.discount_percentage = round(
                (1 - item.product.discount_price / item.product.price) * 100
            )
        else:
            item.product.discount_percentage = 0

    subtotal = sum(item.total_price for item in cart_items)

    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost

    tax = round(subtotal * Decimal("0.05"), 2)

    discount = Decimal("0")
    coupon_code = request.session.get('coupon_code', '')
    coupon_msg = ''
    coupon_error = ''

    if coupon_code and store_settings.discounts_enabled:
        promo = PromoCode.objects.filter(code=coupon_code).first()
        if promo and promo.is_valid:
            discount = round(subtotal * Decimal(promo.discount_percent) / 100, 2)
            coupon_msg = f'"{promo.code}" applied — {promo.discount_percent}% off'
        else:
            request.session.pop('coupon_code', None)
            coupon_code = ''
            coupon_error = 'Coupon is no longer valid.'

    total = subtotal + shipping + tax - discount
    item_count = cart_items.count()
    from_profile = request.GET.get('from') == 'profile'

    return render(request, "user/cart.html", {
        "cart_items": cart_items,
        "item_count": item_count,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "discount": discount,
        "total": total,
        "store_settings": store_settings,
        "coupon_code": coupon_code,
        "coupon_msg": coupon_msg,
        "coupon_error": coupon_error,
        "from_profile": from_profile,
    })

@login_required
def apply_coupon(request):
    from apps.adminpanel.models import StoreSettings, PromoCode

    if request.method == 'POST':
        store_settings = StoreSettings.get_settings()
        code = request.POST.get('coupon_code', '').strip().upper()

        if not store_settings.discounts_enabled:
            messages.error(request, "Discounts are currently disabled.")
            return redirect('home:cart_view')

        promo = PromoCode.objects.filter(code=code).first()
        if not promo:
            messages.error(request, f'"{code}" is not a valid coupon code.')
        elif not promo.is_valid:
            messages.error(request, f'"{code}" has expired or reached its usage limit.')
        else:
            request.session['coupon_code'] = code
            messages.success(request, f'"{code}" applied — {promo.discount_percent}% off!')

    return redirect('home:cart_view')


@login_required
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.success(request, "Coupon removed.")
    return redirect('home:cart_view')


@login_required(login_url='accounts:userlogin')
def update_cart(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "increase":
            if cart_item.quantity < cart_item.product.stock_quantity:
                cart_item.quantity += 1
                cart_item.save()
            else:
                messages.error(request, f"Cannot add more. Only {cart_item.product.stock_quantity} available.")
                return redirect('home:cart_view')

        elif action == "decrease":
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                return redirect('home:cart_view')

    return redirect('home:cart_view')


def get_product_sizes(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    sizes = []
    if product.size:
        sizes = [s.strip() for s in product.size.split(",")]

    primary_image = product.images.first()
    image_url = primary_image.image.url if primary_image else "/static/images/no-image.png"

    return JsonResponse({
        "name": product.product_name,
        "price": product.price,
        "image": image_url,
        "sizes": sizes
    })

@login_required
def move_to_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        if product.stock_quantity <= 0:
            messages.error(request, f"Sorry, '{product.product_name}' is out of stock.")
            return redirect("home:wishlist_view")

        size = request.POST.get("size")

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product_id=product_id,
            defaults={"size": size, "quantity": 1}
        )

        if not created:
            if cart_item.quantity < product.stock_quantity:
                cart_item.quantity += 1
                cart_item.size = size
                cart_item.save()
            else:
                messages.error(request, f"Cannot add more '{product.product_name}'. Only {product.stock_quantity} available.")
                return redirect("home:wishlist_view")

        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        messages.success(request, f"Moved '{product.product_name}' to your bag.")

    return redirect("home:wishlist_view")


@login_required
def remove_cart_item(request, item_id):
    if request.method == "POST":
        Cart.objects.filter(id=item_id, user=request.user).delete()
    return redirect("home:cart_view")

@login_required
def move_to_wishlist(request, item_id):
    if request.method == "POST":
        cart_item = Cart.objects.filter(id=item_id, user=request.user).first()
        if not cart_item:
            return redirect("home:cart_view")
        Wishlist.objects.get_or_create(user=request.user, product=cart_item.product)
        cart_item.delete()
    return redirect("home:cart_view")

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    images = product.images.all()
    sizes = list(product.product_sizes.values('size', 'stock_quantity'))

    if product.discount_price and product.price:
        discount_pct = round((1 - product.discount_price / product.price) * 100)
        product.discount_percentage = discount_pct
    else:
        product.discount_percentage = 0

    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(id=product.id).prefetch_related('images')[:4]

    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()

    return render(request, "user/product_view.html", {
        "product": product,
        "images": images,
        "sizes": sizes,
        "related_products": related_products,
        "is_wishlisted": is_wishlisted,
        "discount_percentage": product.discount_percentage,
    })


@login_required(login_url='accounts:userlogin')
def checkout(request):
    from apps.adminpanel.models import StoreSettings, PromoCode

    store_settings = StoreSettings.get_settings()

    if request.method == "POST" and request.POST.get("buy_now"):
        product_id = request.POST.get("product_id")
        quantity   = int(request.POST.get("quantity", 1))
        size       = request.POST.get("size", "")
        product    = get_object_or_404(Product, id=product_id)

        if quantity > product.stock_quantity:
            messages.error(request, f"Cannot buy {quantity}. Only {product.stock_quantity} available.")
            return redirect(request.META.get('HTTP_REFERER') or 'home:home')
        if product.stock_quantity <= 0:
            messages.error(request, f"Sorry, '{product.product_name}' is out of stock.")
            return redirect(request.META.get('HTTP_REFERER') or 'home:home')

        price    = product.discount_price or product.price
        subtotal = price * quantity
        shipping = Decimal("0")
        if subtotal < store_settings.free_shipping_threshold:
            shipping = store_settings.standard_shipping_cost
        tax   = round(subtotal * Decimal("0.05"), 2)
        total = subtotal + shipping + tax

        buy_now_item = {
            "product":     product,
            "quantity":    quantity,
            "size":        size,
            "total_price": price * quantity,
        }

        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')

        return render(request, "user/checkout.html", {
            "cart_items":         [buy_now_item],
            "item_count":         1,
            "subtotal":           subtotal,
            "shipping":           shipping,
            "tax":                tax,
            "discount":           Decimal("0"),
            "coupon_msg":         "",
            "total":              total,
            "addresses":          addresses,
            "default_address":    addresses.filter(is_default=True).first(),
            "store_settings":     store_settings,
            "buy_now":            True,
            "buy_now_product_id": product_id,
            "buy_now_size":       size,
        })

    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product").prefetch_related("product__images")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("home:cart_view")

    for item in cart_items:
        if item.quantity > item.product.stock_quantity:
            messages.error(request, f"'{item.product.product_name}' only has {item.product.stock_quantity} available.")
            return redirect("home:cart_view")

    subtotal = sum(item.total_price for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost
    tax = round(subtotal * Decimal("0.05"), 2)

    coupon_code = request.session.get('coupon_code', '')
    discount = Decimal("0")
    coupon_msg = ""

    if coupon_code and store_settings.discounts_enabled:
        promo = PromoCode.objects.filter(code=coupon_code).first()
        if promo and promo.is_valid:
            discount = round(subtotal * Decimal(promo.discount_percent) / 100, 2)
            coupon_msg = f'"{coupon_code}" applied — {promo.discount_percent}% off'

    total = subtotal + shipping + tax - discount

    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        delivery   = request.POST.get('delivery', 'standard')

        if not address_id:
            messages.error(request, "Please select a delivery address.", extra_tags='checkout')
            return redirect("home:checkout")

        if not Address.objects.filter(id=address_id, user=request.user).exists():
            messages.error(request, "Invalid address selected.", extra_tags='checkout')
            return redirect("home:checkout")

        request.session['checkout_address_id'] = address_id
        request.session['checkout_delivery']   = delivery
        return redirect('home:checkout_payment')

    return render(request, "user/checkout.html", {
        "cart_items":      cart_items,
        "item_count":      cart_items.count(),
        "subtotal":        subtotal,
        "shipping":        shipping,
        "tax":             tax,
        "discount":        discount,
        "coupon_msg":      coupon_msg,
        "total":           total,
        "addresses":       addresses,
        "default_address": default_address,
        "store_settings":  store_settings,
        "buy_now":         False,
    })


# ── Replace your checkout_payment view and add razorpay_callback below it ─────
# Also add these imports at the top of views.py if not already present:
#
#   import razorpay
#   from django.conf import settings
#   from django.views.decorators.csrf import csrf_exempt
#   import hmac, hashlib, json

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import hmac, hashlib, json


@login_required(login_url='accounts:userlogin')
def checkout_payment(request):
    from apps.adminpanel.models import StoreSettings, PromoCode
    from django.db.models import F

    address_id = request.session.get('checkout_address_id')
    delivery   = request.session.get('checkout_delivery', 'standard')

    if not address_id:
        messages.error(request, "Please complete your address first.", extra_tags='checkout')
        return redirect('home:checkout')

    address    = get_object_or_404(Address, id=address_id, user=request.user)
    cart_items = Cart.objects.filter(
        user=request.user
    ).select_related("product").prefetch_related("product__images")

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("home:cart_view")

    store_settings = StoreSettings.get_settings()

    subtotal = sum(item.total_price for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost
    if delivery == 'express':
        shipping += store_settings.express_shipping_cost
    tax = round(subtotal * Decimal("0.05"), 2)

    coupon_code = request.session.get('coupon_code', '')
    coupon_msg  = ""
    discount    = Decimal("0")
    if coupon_code and store_settings.discounts_enabled:
        promo = PromoCode.objects.filter(code=coupon_code).first()
        if promo and promo.is_valid:
            discount   = round(subtotal * Decimal(promo.discount_percent) / 100, 2)
            coupon_msg = f'"{coupon_code}" applied — {promo.discount_percent}% off'

    total = subtotal + shipping + tax - discount

    # ── COD: place order immediately ──────────────────────────────────────────
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')

        if payment_method == 'cod':
            order = Order.objects.create(
                user=request.user,
                address=address,
                total_amount=total,
                status="pending",
                payment_method="cod",
                shipping_amount=shipping,
                tax_amount=tax,
                discount_amount=discount,
                coupon_code=coupon_code or None,
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.discount_price or item.product.price,
                    size=item.size,
                )
            if coupon_code:
                PromoCode.objects.filter(code=coupon_code).update(used_count=F('used_count') + 1)
                request.session.pop('coupon_code', None)

            cart_items.delete()
            request.session.pop('checkout_address_id', None)
            request.session.pop('checkout_delivery', None)

            messages.success(request, f"Order #{order.id} placed successfully!", extra_tags='checkout')
            return redirect('home:user_orders')

        # ── Razorpay: create Razorpay order, render page with JS ──────────────
        elif payment_method == 'razorpay':
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            amount_paise = int(total * 100)   # Razorpay takes paise

            razorpay_order = client.order.create({
                "amount":   amount_paise,
                "currency": "INR",
                "payment_capture": 1,
            })

            # Persist pending order so we can confirm after payment
            order = Order.objects.create(
                user=request.user,
                address=address,
                total_amount=total,
                status="pending",
                payment_method="razorpay",
                shipping_amount=shipping,
                tax_amount=tax,
                discount_amount=discount,
                coupon_code=coupon_code or None,
                razorpay_order_id=razorpay_order['id'],
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.discount_price or item.product.price,
                    size=item.size,
                )

            # Store in session so callback can verify
            request.session['pending_order_id'] = order.id

            return render(request, "user/payment.html", {
                "address":          address,
                "delivery":         delivery,
                "cart_items":       cart_items,
                "subtotal":         subtotal,
                "shipping":         shipping,
                "tax":              tax,
                "discount":         discount,
                "coupon_msg":       coupon_msg,
                "total":            total,
                "store_settings":   store_settings,
                # Razorpay context
                "razorpay":         True,
                "razorpay_key":     settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_amount":  amount_paise,
                "user_name":        request.user.get_full_name() or request.user.email,
                "user_email":       request.user.email,
                "user_phone":       getattr(address, 'phone', ''),
            })

    # ── GET: render payment selection page ────────────────────────────────────
    return render(request, "user/payment.html", {
        "address":        address,
        "delivery":       delivery,
        "cart_items":     cart_items,
        "subtotal":       subtotal,
        "shipping":       shipping,
        "tax":            tax,
        "discount":       discount,
        "coupon_msg":     coupon_msg,
        "total":          total,
        "store_settings": store_settings,
        "razorpay":       False,
    })


@csrf_exempt
def razorpay_callback(request):
    """Called by Razorpay after payment — verifies signature and confirms order."""
    from apps.adminpanel.models import PromoCode
    from django.db.models import F

    if request.method != 'POST':
        return redirect('home:user_orders')

    razorpay_payment_id  = request.POST.get('razorpay_payment_id', '')
    razorpay_order_id    = request.POST.get('razorpay_order_id', '')
    razorpay_signature   = request.POST.get('razorpay_signature', '')

    # Verify signature
    key_secret = settings.RAZORPAY_KEY_SECRET.encode()
    msg        = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected   = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()

    if not order:
        messages.error(request, "Order not found.")
        return redirect('home:user_orders')

    if hmac.compare_digest(expected, razorpay_signature):
        # Payment verified
        order.status                = "confirmed"
        order.razorpay_payment_id   = razorpay_payment_id
        order.razorpay_signature    = razorpay_signature
        order.save()

        # Clear cart
        Cart.objects.filter(user=order.user).delete()

        # Use coupon
        if order.coupon_code:
            PromoCode.objects.filter(code=order.coupon_code).update(used_count=F('used_count') + 1)

        # Clean session
        request.session.pop('coupon_code', None)
        request.session.pop('checkout_address_id', None)
        request.session.pop('checkout_delivery', None)
        request.session.pop('pending_order_id', None)

        messages.success(request, f"Payment successful! Order #{order.id} confirmed.")
        return redirect('home:order_detail', order_id=order.id)

    else:
        # Signature mismatch — mark as failed
        order.status = "payment_failed"
        order.save()
        messages.error(request, "Payment verification failed. Please contact support.")
        return redirect('home:user_orders')


@login_required
def user_orders(request):
    orders = Order.objects.select_related('user').prefetch_related(
        'items__product'
    ).filter(
        user=request.user
    ).order_by("-created_at")

    selected_period = request.GET.get('period', '6months')

    if selected_period == '6months':
        cutoff = timezone.now() - timedelta(days=180)
        orders = orders.filter(created_at__gte=cutoff)
    elif selected_period in ['2023', '2024', '2025']:
        orders = orders.filter(created_at__year=int(selected_period))

    paginator   = Paginator(orders, 10)
    page        = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)

    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    active_orders_count = Order.objects.filter(
        user=request.user,
        status__in=['pending', 'confirmed', 'processing', 'shipped', 'in_transit']
    ).count()

    return render(request, "user/orders.html", {
        "orders":              orders_page,
        "selected_period":     selected_period,
        "cart_count":          cart_count,
        "wishlist_count":      wishlist_count,
        "active_orders_count": active_orders_count,
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return render(request, "user/order_details.html", {
        "order":      order,
        "cart_count": cart_count,
    })

def search_products(request):
    query    = request.GET.get('q', '').strip()
    products = []

    if query:
        products = Product.objects.filter(
            is_available=True
        ).filter(
            Q(product_name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__category_name__icontains=query) |
            Q(tags__icontains=query)
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
        'query':             query,
        'products':          products,
        'wishlist_products': wishlist_products,
    })


# ── Return system ──────────────────────────────────────────────────────────────

RETURN_REASONS = [
    ("wrong_item",       "Wrong item received"),
    ("damaged",          "Item arrived damaged"),
    ("not_as_described", "Not as described"),
    ("size_issue",       "Size doesn't fit"),
    ("quality_issue",    "Quality not as expected"),
    ("changed_mind",     "Changed my mind"),
    ("other",            "Other"),
]


@login_required(login_url='accounts:userlogin')
def request_return(request, order_id):
    from apps.adminpanel.models import StoreSettings
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Guard: only delivered orders
    if order.status != 'delivered':
        messages.error(request, "Only delivered orders can be returned or exchanged.")
        return redirect('home:order_detail', order_id=order_id)

    # Guard: return window (7 days)
    store_settings = StoreSettings.get_settings()
    window_days = getattr(store_settings, 'return_window_days', 7)
    days_since = (timezone.now() - order.updated_at).days
    if days_since > window_days:
        messages.error(request, f"Return window of {window_days} days has passed.")
        return redirect('home:order_detail', order_id=order_id)

    # Guard: no duplicate active return request
    existing = order.return_requests.exclude(
        status__in=['rejected', 'inspection_failed']
    ).first()
    if existing:
        messages.info(request, "A return request already exists for this order.")
        return redirect('home:return_status', return_id=existing.id)

    eligible_items = order.items.filter(return_status='none')

    if request.method == 'POST':
        return_type    = request.POST.get('return_type', 'return')
        reason         = request.POST.get('reason', '').strip()
        details        = request.POST.get('details', '').strip()
        selected_ids   = request.POST.getlist('item_ids')

        if not reason:
            messages.error(request, "Please select a reason.")
            return redirect('home:return_request', order_id=order_id)

        if not selected_ids:
            messages.error(request, "Please select at least one item.")
            return redirect('home:return_request', order_id=order_id)

        selected_items = order.items.filter(id__in=selected_ids, return_status='none')

        # Create ReturnRequest
        return_req = ReturnRequest.objects.create(
            order=order,
            user=request.user,
            return_type=return_type,
            reason=reason,
            details=details,
            status='requested',
        )
        return_req.items.set(selected_items)

        # Mark items
        selected_items.update(
            return_status='return_requested' if return_type == 'return' else 'exchange_requested',
            return_reason=f"[{return_type.upper()}] {reason}" + (f" — {details}" if details else ""),
            return_requested_at=timezone.now(),
        )

        # Update order status
        order.status = 'return_requested'
        order.save()

        return redirect('home:return_status', return_id=return_req.id)

    reasons = [
        ("wrong_item",       "Wrong item received"),
        ("damaged",          "Item arrived damaged"),
        ("not_as_described", "Not as described"),
        ("size_issue",       "Size doesn't fit"),
        ("quality_issue",    "Quality not as expected"),
        ("changed_mind",     "Changed my mind"),
        ("other",            "Other"),
    ]

    return render(request, 'user/return_request.html', {
        'order':          order,
        'eligible_items': eligible_items,
        'reasons':        reasons,
    })


@login_required(login_url='accounts:userlogin')
def return_status(request, return_id):
    return_req = get_object_or_404(ReturnRequest, id=return_id, user=request.user)

    # If approved and self-ship: allow uploading tracking info
    if request.method == 'POST' and return_req.status == 'approved':
        tracking = request.POST.get('tracking_number', '').strip()
        courier  = request.POST.get('courier_name', '').strip()
        if tracking and courier:
            return_req.tracking_number = tracking
            return_req.courier_name    = courier
            return_req.status          = 'in_transit'
            return_req.save()
            messages.success(request, "Tracking info submitted. We'll update you when received.")
            return redirect('home:return_status', return_id=return_req.id)

    return render(request, 'user/return_status.html', {'return_req': return_req})


@login_required(login_url='accounts:userlogin')
def return_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return_req = order.return_requests.last()
    if return_req:
        return redirect('home:return_status', return_id=return_req.id)
    return render(request, 'user/return_success.html', {'order': order})




@login_required(login_url='accounts:userlogin')
def upload_return_tracking(request, item_id):
    """Customer uploads courier tracking info after self-shipping their return."""
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.return_status != 'return_approved':
        messages.error(request, "This item is not approved for return yet.")
        return redirect('home:order_detail', order_id=item.order_id)

    if request.method == 'POST':
        tracking = request.POST.get('tracking_number', '').strip()
        courier  = request.POST.get('courier_name', '').strip()

        if not tracking or not courier:
            messages.error(request, "Please provide both courier name and tracking number.")
            return redirect('home:upload_return_tracking', item_id=item_id)

        item.tracking_number = tracking
        item.courier_name    = courier
        item.return_status   = 'in_transit'
        item.save()

        messages.success(request, "Tracking details saved. We'll update you when it arrives.")
        return redirect('home:order_detail', order_id=item.order_id)

    return render(request, 'user/upload_tracking.html', {'item': item})


# ── Remaining views ────────────────────────────────────────────────────────────

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        if order.status in ['pending', 'confirmed']:
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Order #{order.id} has been cancelled.')
        else:
            messages.error(request, 'This order cannot be cancelled.')
    return redirect('home:user_orders')

@login_required
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user/order_invoice.html', {'order': order})

def privacy_policy(request):
    return render(request, 'user/footer/privacy_policy.html')

def refund_policy(request):
    return render(request, 'user/footer/refund_policy.html')

def shipping_policy(request):
    return render(request, 'user/footer/shipping_policy.html')
def terms_of_service(request):
    return render(request, 'user/footer/terms_of_service.html')
def contact_info(request):
    return render(request, 'user/footer/contact_info.html')
