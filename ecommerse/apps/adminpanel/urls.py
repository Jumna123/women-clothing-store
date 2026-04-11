from django.urls import path
from .views.dashboard import admin_dashboard
from .views.products import product, addproduct, delete_Product, delete_product_image, edit_product
from .views.category import category, add_category, category_toggle_status, edit_category, delete_category
from .views.collections import collections_list, addcollections, edit_collection, delete_collection
from .views.orders import (
    orders, order_detail, update_order_status,
    handle_return, handle_return_item, return_requests,
    export_orders,
)
from .views.admin_settings import admin_settings, toggle_promo, delete_promo
from .views.user import user_management, block_user, activate_user

app_name = 'adminpanel'

urlpatterns = [
    path('dashboard/',                           admin_dashboard,         name='dashboard'),
    path('product/',                             product,                 name='product'),
    path('category/',                            category,                name='category'),
    path('add_category/',                        add_category,            name='add-category'),
    path('addproduct/',                          addproduct,              name='addproduct'),
    path('collections/',                         collections_list,        name='collections'),
    path('addcollections/',                      addcollections,          name='addcollections'),
    path('collections/edit/<int:id>/',           edit_collection,         name='editcollection'),
    path('collections/delete/<int:id>/',         delete_collection,       name='deletecollection'),
    path('users/',                               user_management,         name='users'),
    path('settings/',                            admin_settings,          name='settings'),
    path('users/block/<int:user_id>/',           block_user,              name='block_user'),
    path('users/activate/<int:user_id>/',        activate_user,           name='activate_user'),
    path('category/toggle-status/<int:pk>/',     category_toggle_status,  name='toggle-category-status'),
    path('category/edit/<int:pk>/',              edit_category,           name='edit-category'),
    path('category/delete/<int:pk>/',            delete_category,         name='delete-category'),
    path('Product/delete/<int:pk>/',             delete_Product,          name='delete-product'),
    path('Product/edit/<int:pk>/',               edit_product,            name='edit-product'),
    path('product-image/delete/<int:pk>/',       delete_product_image,    name='delete_product_image'),

    # ── Orders ────────────────────────────────────────────────────────────────
    path('orders/',                              orders,                  name='orders'),
    path('orders/<int:pk>/',                     order_detail,            name='order-detail'),
    path('orders/update-status/<int:pk>/',       update_order_status,     name='update-order-status'),
    path('orders/export/',                       export_orders,           name='export-orders'),

    # ── Returns ───────────────────────────────────────────────────────────────
    path('returns/',                             return_requests,         name='return_requests'),
    path('orders/handle-return/<int:pk>/',       handle_return,           name='handle-return'),
    # ── Settings / Promos ─────────────────────────────────────────────────────
    path('settings/promo/toggle/<int:pk>/',      toggle_promo,            name='toggle-promo'),
    path('settings/promo/delete/<int:pk>/',      delete_promo,            name='delete-promo'),

    path('returns/',                          return_requests,   name='return_requests'),
    path('returns/item/<int:item_id>/action/', handle_return_item, name='handle-return-item'),
]