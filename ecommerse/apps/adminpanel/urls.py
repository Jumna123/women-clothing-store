from django.urls import path
from .views.dashboard import admin_dashboard
from .views.products import product
from .views.products import addproduct
from .views.category import category,add_category
from .views.collections import collections,addcollections,edit_collection,delete_collection
from .views.orders import orders
from .views.admin_settings import admin_settings
from .views.user import user_management, block_user, activate_user
from .views.category import category_toggle_status
from .views.category import edit_category
from .views.category import delete_category
from .views.products import delete_Product,delete_product_image
from .views.products import edit_product
from .views.orders import orders, update_order_status, handle_return,export_orders
from .views.admin_settings import admin_settings, toggle_promo, delete_promo





app_name = 'adminpanel'
 
urlpatterns = [
    path('dashboard/',admin_dashboard, name='dashboard'),
    path('product/',product,name='product'),
    path('category/',category,name='category'),
    path('add_category/',add_category,name='add-category'),
    path('addproduct/',addproduct,name='addproduct'),
    path('collections/',collections,name='collections'),
    path('addcollections/',addcollections,name='addcollections'),
    path("collections/edit/<int:id>/", edit_collection, name="editcollection"),
    path("collections/delete/<int:id>/", delete_collection, name="deletecollection"),
    path('users/',user_management,name='users'),
    path('settings/',admin_settings,name='settings'),
    path("users/block/<int:user_id>/", block_user, name="block_user"),
    path("users/activate/<int:user_id>/", activate_user, name="activate_user"),
    path('category/toggle-status/<int:pk>/', category_toggle_status, name='toggle-category-status'),
    path("category/edit/<int:pk>/",edit_category,name="edit-category"),
    path("category/delete/<int:pk>/",delete_category,name="delete-category"),
    path("Product/delete/<int:pk>/",delete_Product,name="delete-product"),
    path("Product/edit/<int:pk>/",edit_product,name="edit-product"),
    path("product-image/delete/<int:pk>/", delete_product_image, name="delete_product_image"),
    path('orders/', orders, name='orders'),
    path('orders/update-status/<int:pk>/', update_order_status, name='update-order-status'),
    path('orders/handle-return/<int:pk>/', handle_return, name='handle-return'),
    path('orders/export/', export_orders, name='export-orders'),
    path('settings/', admin_settings, name='settings'),
    path('settings/promo/toggle/<int:pk>/', toggle_promo, name='toggle-promo'),
    path('settings/promo/delete/<int:pk>/', delete_promo, name='delete-promo'),

]
