from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from ..forms import CollectionForm
from apps.adminpanel.models import Collection
import base64
from django.core.files.base import ContentFile


def collections(request):
    collections = Collection.objects.prefetch_related('products').all()
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
