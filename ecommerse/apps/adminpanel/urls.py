from django.urls import path
from .views.dashboard import admin_dashboard
from .views.products import product
from .views.products import addproduct
from .views.category import category
from .views.collections import collections
from .views.collections import addcollections
from .views.orders import orders
from .views.user import users

app_name = 'adminpanel'
 
urlpatterns = [
    path('dashboard/',admin_dashboard, name='dashboard'),
    path('product/',product,name='product'),
    path('category/',category,name='category'),
    path('addproduct/',addproduct,name='addproduct'),
    path('collections/',collections,name='collections'),
    path('addcollections/',addcollections,name='addcollections'),
    path('orders/',orders,name='orders'),
    path('users/',users,name='users'),
]
