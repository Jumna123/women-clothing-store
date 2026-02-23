from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from ..forms import CollectionForm
from apps.adminpanel.models import Collection

def collections(request):
    collections = Collection.objects.all()
    return render(request, "adminpanel/collections.html", {
        "collections": collections
    })


def addcollections(request):
    form = CollectionForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("adminpanel:collections")

    return render(request, "adminpanel/addcollection.html", {
        "form": form
    })

def edit_collection(request, id):
    collection = get_object_or_404(Collection, id=id)

    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        if form.is_valid():
            form.save()
            messages.success(request, "Collection updated successfully")
            return redirect("adminpanel:collections")
    else:
        form = CollectionForm(instance=collection)

    return render(request, "adminpanel/addcollection.html", {
        "form": form,
        "collection": collection,
        "is_edit": True,
    })

@require_POST
def delete_collection(request, id):
    collection = get_object_or_404(Collection, id=id)
    collection.delete()
    messages.success(request, "Collection deleted successfully")
    return redirect("adminpanel:collections")
