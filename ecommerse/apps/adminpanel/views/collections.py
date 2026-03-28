from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from ..forms import CollectionForm
from apps.adminpanel.models import Collection
import base64
from django.core.files.base import ContentFile
from ..models import Product,ProductImage
from apps.home.models import Wishlist

from django.core.paginator import Paginator
from django.db.models import Prefetch

def collections(request, pk):
    collection = get_object_or_404(Collection, pk=pk, is_active=True)

    products = Product.objects.filter(
        collections=collection
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )

    # Filter
    availability = request.GET.get('availability', '')
    if availability == 'in_stock':
        products = products.filter(is_available=True, stock_quantity__gt=0)
    elif availability == 'sold_out':
        products = products.filter(stock_quantity=0)

    # Sort
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
        "category": collection,
        "products": products,
        "wishlist_products": wishlist_products,
        "is_collection": True,
        "current_availability": availability,
        "current_sort": sort,
    })

def collections_list(request):
    collections = Collection.objects.all().order_by('-created_at')
    return render(request, "adminpanel/collections.html", {
        "collections": collections
    })

from django.utils import timezone

def addcollections(request):
    form = CollectionForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            collection = form.save(commit=False)

            cropped_data = request.POST.get("cropped_image")
            if cropped_data and cropped_data.startswith("data:image"):
                format, imgstr = cropped_data.split(";base64,")
                ext = format.split("/")[-1]
                collection.image = ContentFile(
                    base64.b64decode(imgstr),
                    name=f"collection_{collection.name}.{ext}"
                )

            collection.save()
            messages.success(request, "Collection created successfully.")  # ← add this
            return redirect("adminpanel:collections")

    return render(request, "adminpanel/addcollection.html", {
        "form": form,
        "today": timezone.now().date(),
    })


def edit_collection(request, id):
    collection = get_object_or_404(Collection, id=id)

    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        if form.is_valid():
            collection = form.save(commit=False)

            # ✅ handle cropped image
            cropped_data = request.POST.get("cropped_image")
            if cropped_data and cropped_data.startswith("data:image"):
                format, imgstr = cropped_data.split(";base64,")
                ext = format.split("/")[-1]
                collection.image = ContentFile(
                    base64.b64decode(imgstr),
                    name=f"collection_{collection.name}.{ext}"
                )

            collection.save()
            messages.success(request, "Collection updated successfully")
            return redirect("adminpanel:collections")
    else:
        form = CollectionForm(instance=collection)

    return render(request, "adminpanel/addcollection.html", {
        "form": form,
        "collection": collection,
        "is_edit": True,
        "today": timezone.now().date(),
    })



@require_POST
def delete_collection(request, id):
    collection = get_object_or_404(Collection, id=id)
    collection.delete()
    messages.success(request, "Collection deleted successfully")
    return redirect("adminpanel:collections")
