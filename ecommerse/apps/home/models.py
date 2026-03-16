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

    size = models.CharField(max_length=10, blank=True, null=True)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size')

    def total_price(self):
        if self.product.discount_price:
            return self.product.discount_price * self.quantity
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user.email} - {self.product.product_name}"
    
class Order(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("return_requested", "Return Requested"),
        ("returned", "Returned"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("stripe", "Online Payment"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    # Add these missing fields:
    address = models.ForeignKey(
        'accounts.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cod"
    )
    return_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def can_return(self):
        """Only delivered orders within 7 days can be returned."""
        from django.utils import timezone
        if self.status != 'delivered':
            return False
        days_since_delivery = (timezone.now() - self.updated_at).days
        return days_since_delivery <= 7

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    size = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.product_name} ({self.quantity})"