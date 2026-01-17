from django.db import models

class Category(models.Model):
    category_image=models.ImageField()
    category_name=models.CharField(max_length=20)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)
    slug=models.SlugField(unique=True)
    updated_at=models.DateTimeField(auto_now=True)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products')
    
    description=models.TextField()
    fabric=models.CharField(max_length=20)
    colour=models.CharField(max_length=30)
    
    product_name=models.CharField(max_length=20)
    product_code=models.CharField(max_length=20)
    size=models.CharField(max_length=10)
    slug=models.SlugField(unique=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True)
    
    
    stock_quantity=models.IntegerField()
    is_available=models.BooleanField(default=True)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)



# Create your models here.
