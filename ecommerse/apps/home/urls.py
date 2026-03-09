# apps/home/urls.py

from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:slug>/", views.category_products, name="category_products"),
    path('wishlist', views.wishlist_view, name='wishlist_view'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart_view"),
    path("update-cart/<int:item_id>/", views.update_cart, name="update_cart"),
    path("get-product-sizes/<int:product_id>/", views.get_product_sizes),
    path("move-to-cart/<int:product_id>/", views.move_to_cart, name="move_to_cart"),
    path("remove-cart-item/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("move-to-wishlist/<int:item_id>/", views.move_to_wishlist, name="move_to_wishlist"),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.user_orders, name="user_orders"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("checkout/place-order/", views.place_order, name="place_order"),
    path("collection/<int:pk>/", views.collection_products, name="collection_products"),

]
