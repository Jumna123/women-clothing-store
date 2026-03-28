from django.contrib import admin

from .models import Category
from .models import Product
from .models import ProductImage
from .models import Collection



# Register your models here.

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Collection)

