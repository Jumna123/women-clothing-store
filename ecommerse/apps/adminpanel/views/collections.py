from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from ..forms import CollectionForm
from apps.adminpanel.models import Collection
import base64
from django.core.files.base import ContentFile


from django.core.paginator import Paginator

def collections(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    collections_qs = Collection.objects.prefetch_related('products').all()

    if q:
        collections_qs = collections_qs.filter(name__icontains=q)

    if status == 'active':
        collections_qs = collections_qs.filter(is_active=True, status='published')
    elif status == 'draft':
        collections_qs = collections_qs.filter(status='draft')

    paginator = Paginator(collections_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "adminpanel/collections.html", {
        "collections": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
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
