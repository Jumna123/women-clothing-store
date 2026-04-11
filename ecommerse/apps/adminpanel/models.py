from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator


class Category(models.Model):
    category_image = models.ImageField(upload_to="categories/", blank=True, null=True)
    category_name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category_name


from django.utils import timezone

class Collection(models.Model):
    STATUS_CHOICES = [("published", "Published"), ("draft", "Draft")]
    VISIBILITY_CHOICES = [("public", "Public"), ("private", "Private")]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="collections/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    publish_at = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="public")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def products_count(self):
        return self.products.count()

    @property
    def computed_status(self):
        if not self.is_active:
            return "draft"
        if self.publish_at and self.publish_at > timezone.now().date():
            return "draft"
        return "published"

    @property
    def computed_visibility(self):
        if not self.is_active:
            return "private"
        if self.publish_at and self.publish_at > timezone.now().date():
            return "private"
        return "public"

    @property
    def is_scheduled(self):
        return self.publish_at and self.publish_at > timezone.now().date()

    def save(self, *args, **kwargs):
        if not self.is_active:
            self.status = "draft"
            self.visibility = "private"
        elif self.publish_at and self.publish_at > timezone.now().date():
            self.status = "draft"
            self.visibility = "private"
        else:
            self.status = "published"
            self.visibility = "public"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    collections = models.ManyToManyField(Collection, blank=True, related_name='products')
    product_name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    fabric = models.CharField(max_length=20, blank=True)
    color_hex = models.CharField(max_length=7, blank=True, null=True)
    color_name = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)  # keep as overall fallback
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_trending = models.BooleanField(default=False)
    tags = models.CharField(max_length=500, blank=True, default="")
    size = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.product_name


# ← Outside Product class, at the same indentation level
class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_sizes')
    size = models.CharField(max_length=20)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('product', 'size')

    def __str__(self):
        return f"{self.product.product_name} - {self.size} ({self.stock_quantity})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.product_name}"


class StoreSettings(models.Model):
    store_name = models.CharField(max_length=100, default="vólke shoppe")
    marquee_text = models.TextField(
        default="Free shipping on orders over ₹1000 | New arrivals every week | Use code WELCOME10 for 10% off",
        help_text="Separate multiple messages with |"
    )
    cod_enabled = models.BooleanField(default=True)
    discounts_enabled = models.BooleanField(default=True)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    standard_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    express_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=15)
    return_window_days = models.PositiveIntegerField(default=10)  # ← add this
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Store Settings"

    def __str__(self):
        return "Store Settings"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='promos/', null=True, blank=True)
    show_on_homepage = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        if self.expires_at and self.expires_at < timezone.now().date():
            return False
        return True