from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    category_image = models.ImageField(upload_to="categories/",blank=True,null=True)
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

class Collection(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="collections/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    publish_at = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )
    collections = models.ManyToManyField(
        Collection,
        blank=True,
        related_name='products'
    )


    product_name = models.CharField(max_length=50)
    
    slug = models.SlugField(unique=True, blank=True)

    description = models.TextField(blank=True)
    fabric = models.CharField(max_length=20, blank=True)
    color_hex = models.CharField(max_length=7, blank=True, null=True)   
    color_name = models.CharField(max_length=50, blank=True, null=True)  
    size = models.CharField(max_length=100, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    image = models.ImageField(upload_to="products/",null=True,blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.product_name)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.product_name}"



