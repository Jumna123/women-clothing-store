from django.shortcuts import render, get_object_or_404
from apps.adminpanel.models import Category, Product


def home(request):
    from apps.adminpanel.models import Category
    from apps.adminpanel.models import Collection
    categories = Category.objects.all()
    collections=Collection.objects.all()
    return render(request, "user/home.html", {
        "categories": categories,
        "collections":collections
    })



from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch
from apps.adminpanel.models import Category, Product, ProductImage

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

    return render(request, "user/product_listingpage.html", {
        "category": category,
        "products": products
    })

