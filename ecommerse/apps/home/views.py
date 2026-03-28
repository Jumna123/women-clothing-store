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
from apps.adminpanel.models import Category, Product, ProductImage, Collection, ProductSize  # add ProductSize
from apps.accounts.models import Address
from .models import Wishlist, Cart, Order, OrderItem


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

    from .models import Cart

@login_required(login_url='accounts:userlogin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.GET.get('size', '')
    quantity_to_add = int(request.GET.get('quantity', 1))

    # Check per-size stock if sizes exist
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

    # ADD THIS LINE
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
        "from_profile": from_profile,  # ADD THIS
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

    return JsonResponse({
        "name": product.product_name,
        "price": product.price,
        "image": product.image.url,
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
            defaults={
                "size": size,
                "quantity": 1
            }
        )

        # If already exists → increase quantity
        if not created:
            if cart_item.quantity < product.stock_quantity:
                cart_item.quantity += 1
                cart_item.size = size  # optional: update size
                cart_item.save()
            else:
                messages.error(request, f"Cannot add more '{product.product_name}'. Only {product.stock_quantity} available.")
                return redirect("home:wishlist_view")

        # Remove from wishlist
        Wishlist.objects.filter(
            user=request.user,
            product_id=product_id
        ).delete()
        
        messages.success(request, f"Moved '{product.product_name}' to your bag.")

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
    product = get_object_or_404(Product, slug=slug)
    images = product.images.all()
    sizes = list(product.product_sizes.values('size', 'stock_quantity'))  

    # Discount percentage
    if product.discount_price and product.price:
        discount_pct = round((1 - product.discount_price / product.price) * 100)
        product.discount_percentage = discount_pct
    else:
        product.discount_percentage = 0

    # Related products — same category, exclude current
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(id=product.id).prefetch_related('images')[:4]

    # Wishlist check
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    return render(request, "user/product_view.html", {
        "product": product,
        "images": images,
        "sizes": sizes,  
        "related_products": related_products,
        "is_wishlisted": is_wishlisted,
        "discount_percentage": product.discount_percentage,
    })



from apps.accounts.models import Address
from apps.adminpanel.models import StoreSettings

@login_required(login_url='accounts:userlogin')
def checkout(request):
    from apps.adminpanel.models import StoreSettings, PromoCode

    store_settings = StoreSettings.get_settings()

    # ── Buy Now (single product) ──────────────────────────
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
        tax      = round(subtotal * Decimal("0.05"), 2)
        total    = subtotal + shipping + tax

        buy_now_item = {
            "product":     product,
            "quantity":    quantity,
            "size":        size,
            "total_price": price * quantity,
        }

        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')

        return render(request, "user/checkout.html", {
            "cart_items":         [buy_now_item],
            "subtotal":           subtotal,
            "shipping":           shipping,
            "tax":                tax,
            "discount":           Decimal("0"),
            "total":              total,
            "addresses":          addresses,
            "default_address":    addresses.filter(is_default=True).first(),
            "store_settings":     store_settings,
            "buy_now":            True,
            "buy_now_product_id": product_id,
            "buy_now_size":       size,
        })

    # ── Normal cart checkout ──────────────────────────────
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

    # Carry coupon from cart session
    coupon_code = request.session.get('checkout_coupon')
    discount = Decimal(str(request.session.get('checkout_discount', 0)))
    if coupon_code and store_settings.discounts_enabled:
        promo = PromoCode.objects.filter(code=coupon_code).first()
        if promo and promo.is_valid:
            discount = round(subtotal * Decimal(promo.discount_percent) / 100, 2)

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

        # ADD THESE TWO LINES
        request.session['checkout_discount'] = float(discount)
        request.session['checkout_coupon'] = coupon_code

        return redirect('home:checkout_payment')

    return render(request, "user/checkout.html", {
        "cart_items":      cart_items,
        "subtotal":        subtotal,
        "shipping":        shipping,
        "tax":             tax,
        "discount":        discount,
        "total":           total,
        "addresses":       addresses,
        "default_address": default_address,
        "store_settings":  store_settings,
        "buy_now":         False,
    })


@login_required(login_url='accounts:userlogin')
def checkout_payment(request):
    from apps.adminpanel.models import StoreSettings, PromoCode
    from django.db.models import F

    address_id = request.session.get('checkout_address_id')
    delivery   = request.session.get('checkout_delivery', 'standard')

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

    subtotal = sum(item.total_price for item in cart_items)
    shipping = Decimal("0")
    if subtotal > Decimal("0") and subtotal < store_settings.free_shipping_threshold:
        shipping = store_settings.standard_shipping_cost
    if delivery == 'express':
        shipping += store_settings.express_shipping_cost
    tax = round(subtotal * Decimal("0.05"), 2)

    # Carry coupon discount
    coupon_code = request.session.get('coupon_code', '')
    discount = Decimal("0")
    if coupon_code and store_settings.discounts_enabled:
        promo = PromoCode.objects.filter(code=coupon_code).first()
        if promo and promo.is_valid:
            discount = round(subtotal * Decimal(promo.discount_percent) / 100, 2)

    total = subtotal + shipping + tax - discount

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')

        order = Order.objects.create(
        user=request.user,
        address=address,
        total_amount=total,
        status="pending",
        payment_method=payment_method,
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

        # Increment promo used_count and clear from session
        if coupon_code:
            PromoCode.objects.filter(code=coupon_code).update(used_count=F('used_count') + 1)
            request.session.pop('coupon_code', None)

        cart_items.delete()
        request.session.pop('checkout_address_id', None)
        request.session.pop('checkout_delivery', None)

        messages.success(request, f"Order #{order.id} placed successfully!", extra_tags='checkout')
        return redirect('home:user_orders')

    return render(request, "user/payment.html", {
        "address":        address,
        "delivery":       delivery,
        "cart_items":     cart_items,
        "subtotal":       subtotal,
        "shipping":       shipping,
        "tax":            tax,
        "discount":       discount,
        "total":          total,
        "store_settings": store_settings,
    })



@login_required
def user_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at")

    # --- Period filter ---
    selected_period = request.GET.get('period', '6months')

    if selected_period == '6months':
        cutoff = timezone.now() - timedelta(days=180)
        orders = orders.filter(created_at__gte=cutoff)
    elif selected_period in ['2023', '2024', '2025']:
        orders = orders.filter(created_at__year=int(selected_period))
    # 'all' → no date filter

    # --- Pagination ---
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)

    # --- Sidebar counts ---
    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    active_orders_count = Order.objects.filter(
        user=request.user,
        status__in=['pending', 'confirmed', 'processing', 'shipped', 'in_transit']
    ).count()

    return render(request, "user/orders.html", {
        "orders": orders_page,
        "selected_period": selected_period,
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
        "active_orders_count": active_orders_count,
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    cart_count = Cart.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return render(request, "user/order_details.html", {
        "order": order,
        "cart_count": cart_count,
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
            Q(category__category_name__icontains=query) |
            Q(tags__icontains=query)  # ← only this line is new
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

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        if order.status in ['pending', 'confirmed']:
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Order #{order.order_id} has been cancelled.')
        else:
            messages.error(request, 'This order cannot be cancelled.')
    return redirect('home:user_orders')

@login_required
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user/order_invoice.html', {'order': order})