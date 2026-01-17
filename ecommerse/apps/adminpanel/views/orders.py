from django.shortcuts import render

def orders(request):
    return render(request,"adminpanel/order.html")