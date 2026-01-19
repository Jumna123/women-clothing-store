from django.urls import path
from .views.dashboard import admin_dashboard
from .views.products import product
from .views.products import addproduct
from .views.category import category
from .views.category import add_category
from .views.collections import collections
from .views.collections import addcollections
from .views.orders import orders
from .views.admin_settings import admin_settings
from .views.user import user_management, block_user, activate_user


app_name = 'adminpanel'
 
urlpatterns = [
    path('dashboard/',admin_dashboard, name='dashboard'),
    path('product/',product,name='product'),
    path('category/',category,name='category'),
    path('add_category/',add_category,name='add-category'),
    path('addproduct/',addproduct,name='addproduct'),
    path('collections/',collections,name='collections'),
    path('addcollections/',addcollections,name='addcollections'),
    path('orders/',orders,name='orders'),
    path('users/',user_management,name='users'),
    path('settings/',admin_settings,name='settings'),
    path("users/block/<int:user_id>/", block_user, name="block_user"),
    path("users/activate/<int:user_id>/", activate_user, name="activate_user"),
]
