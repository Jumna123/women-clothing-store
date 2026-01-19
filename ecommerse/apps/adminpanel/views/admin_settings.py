from django.shortcuts import render

def admin_settings(request):
    return render(request,"adminpanel/adminsettings.html")