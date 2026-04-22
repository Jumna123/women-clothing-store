from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.adminpanel.models import Product, Category, Collection  
class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['home:home', 'home:search_products', 'home:contact_info',
                'home:privacy_policy', 'home:shipping_policy', 'home:refund_policy']

    def location(self, item):
        return reverse(item)

class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_available=True)  

    def location(self, obj):
        return reverse('home:product_detail', args=[obj.slug])

class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('home:category_products', args=[obj.slug])

class CollectionSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Collection.objects.all()

    def location(self, obj):
        return reverse('home:collection_products', args=[obj.pk])