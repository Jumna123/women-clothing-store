from django.db import models
from django.conf import settings
from apps.adminpanel.models import Product


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_wishlist')
        ]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.product_name}"


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_products"
    )
    quantity = models.PositiveIntegerField(default=1)
    size     = models.CharField(max_length=10, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size')

    @property
    def total_price(self):
        if self.product.discount_price:
            return self.product.discount_price * self.quantity
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user.email} - {self.product.product_name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending",          "Pending"),
        ("confirmed",        "Confirmed"),
        ("processing",       "Processing"),
        ("shipped",          "Shipped"),
        ("in_transit",       "In Transit"),
        ("delivered",        "Delivered"),
        ("cancelled",        "Cancelled"),
        ("payment_failed",   "Payment Failed"),   # ← add this
        ("return_requested", "Return Requested"),
        ("returned",         "Returned"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod",      "Cash on Delivery"),
        ("razorpay", "Online Payment"),    
    ]


    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    address = models.ForeignKey(
        'accounts.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    payment_method    = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod")
    return_reason     = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)
    total_amount      = models.DecimalField(max_digits=10, decimal_places=2)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    discount_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code       = models.CharField(max_length=50, blank=True, null=True)

    # ── Razorpay ──────────────────────────────────────────────────────────────────
    razorpay_order_id   = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def order_id(self):
        return f"ORD-{self.id:04d}"

    @property
    def can_return(self):
        """True only if delivered within 7 days and has eligible items."""
        from django.utils import timezone
        if self.status != 'delivered':
            return False
        days_since = (timezone.now() - self.updated_at).days
        return days_since <= 7


class OrderItem(models.Model):

    RETURN_STATUS_CHOICES = [
        ('none',                  'None'),
        ('return_requested',      'Return Requested'),
        ('exchange_requested',    'Exchange Requested'),
        ('return_approved',       'Return Approved'),
        ('return_rejected',       'Return Rejected'),
        ('pickup_scheduled',      'Pickup Scheduled'),
        ('picked_up',             'Picked Up'),
        ('in_transit',            'In Transit'),
        ('received_at_warehouse', 'Received at Warehouse'),
        ('inspection_passed',     'Inspection Passed'),
        ('inspection_failed',     'Inspection Failed'),
        ('refund_initiated',      'Refund Initiated'),
        ('refund_processing',     'Refund Processing'),
        ('refunded',              'Refunded'),
        ('returned',              'Returned'),
        ('exchanged',             'Exchanged'),
    ]

    order   = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    size     = models.CharField(max_length=10, blank=True, null=True)

    # ── Return tracking ────────────────────────────────────────────────────────
    return_status       = models.CharField(max_length=30, choices=RETURN_STATUS_CHOICES, default='none')
    return_reason       = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(blank=True, null=True)

    # Pickup / self-ship
    pickup_scheduled_at = models.DateTimeField(blank=True, null=True)
    tracking_number     = models.CharField(max_length=100, blank=True, null=True)
    courier_name        = models.CharField(max_length=100, blank=True, null=True)

    # Inspection
    inspection_notes = models.TextField(blank=True, null=True)
    inspected_at     = models.DateTimeField(blank=True, null=True)

    # Refund
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_method = models.CharField(max_length=50, blank=True, null=True)
    refunded_at   = models.DateTimeField(blank=True, null=True)

    @property
    def subtotal(self):
        return self.quantity * self.price

    @property
    def is_returnable(self):
        from django.utils import timezone
        if self.return_status != 'none':
            return False
        if self.order.status != 'delivered':
            return False
        days = (timezone.now() - self.order.updated_at).days
        return days <= 7

    def __str__(self):
        return f"{self.product.product_name} ({self.quantity})"
    

class ReturnRequest(models.Model):

    RETURN_STATUS_CHOICES = [
        ('requested',         'Return Requested'),
        ('approved',          'Return Approved'),
        ('rejected',          'Return Rejected'),
        ('pickup_scheduled',  'Pickup Scheduled'),
        ('picked_up',         'Picked Up'),
        ('in_transit',        'In Transit to Warehouse'),
        ('received',          'Received at Warehouse'),
        ('inspection_passed', 'Inspection Passed'),
        ('inspection_failed', 'Inspection Failed'),
        ('refund_initiated',  'Refund Initiated'),
        ('refund_processing', 'Refund Processing'),
        ('refunded',          'Refunded'),
    ]

    RETURN_TYPE_CHOICES = [
        ('return',   'Return'),
        ('exchange', 'Exchange'),
    ]

    REFUND_METHOD_CHOICES = [
        ('original', 'Original Payment Method'),
        ('bank',     'Bank Transfer'),
        ('upi',      'UPI'),
        ('wallet',   'Store Wallet'),
    ]

    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    items       = models.ManyToManyField(OrderItem, related_name='return_requests')
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    return_type     = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES, default='return')
    reason          = models.CharField(max_length=100)
    details         = models.TextField(blank=True)
    status          = models.CharField(max_length=30, choices=RETURN_STATUS_CHOICES, default='requested')

    tracking_number  = models.CharField(max_length=100, blank=True)
    courier_name     = models.CharField(max_length=100, blank=True)
    inspection_notes = models.TextField(blank=True)

    refund_method   = models.CharField(max_length=20, choices=REFUND_METHOD_CHOICES, blank=True)
    refund_amount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_ref      = models.CharField(max_length=100, blank=True)

    admin_notes     = models.TextField(blank=True)
    rejected_reason = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return #{self.id} — Order #{self.order.id}"

    @property
    def total_refund_amount(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def timeline_steps(self):
        all_steps = [
            ('requested',         'Return Requested',       'assignment_return'),
            ('approved',          'Admin Approved',          'thumb_up'),
            ('pickup_scheduled',  'Pickup Scheduled',        'local_shipping'),
            ('picked_up',         'Picked Up',               'inventory_2'),
            ('in_transit',        'In Transit',              'directions_car'),
            ('received',          'Received at Warehouse',   'warehouse'),
            ('inspection_passed', 'Inspection Passed',       'verified'),
            ('refund_initiated',  'Refund Initiated',        'payments'),
            ('refund_processing', 'Refund Processing',       'autorenew'),
            ('refunded',          'Refunded',                'check_circle'),
        ]

        # Failed paths
        failed_statuses = ['rejected', 'inspection_failed']
        if self.status in failed_statuses:
            return [{
                'label':   'Return Requested', 'icon': 'assignment_return',
                'done': True, 'current': False,
            }, {
                'label':   'Rejected' if self.status == 'rejected' else 'Inspection Failed',
                'icon':    'cancel', 'done': False, 'current': True,
            }]

        order_map = {s[0]: i for i, s in enumerate(all_steps)}
        current_index = order_map.get(self.status, 0)

        return [
            {
                'label':   label,
                'icon':    icon,
                'done':    order_map.get(key, 0) < current_index,
                'current': key == self.status,
            }
            for key, label, icon in all_steps
        ]