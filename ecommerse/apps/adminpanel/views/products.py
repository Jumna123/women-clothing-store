from django.shortcuts import render

def product(request):
    return render(request,"adminpanel/products.html")

def addproduct(request):
    return render(request,"adminpanel/addproduct.html")