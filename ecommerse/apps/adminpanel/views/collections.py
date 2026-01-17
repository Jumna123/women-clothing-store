from django.shortcuts import render

def collections(request):
    return render(request,"adminpanel/collections.html")

def addcollections(request):
    return render(request,"adminpanel/addcollection.html")