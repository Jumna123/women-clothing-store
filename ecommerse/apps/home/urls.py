from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:slug>/", views.category_products, name="category_products"),
    path("collection/<int:pk>/", views.collection_products, name="collection_products"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("search/", views.search_products, name="search_products"),

    # Wishlist
    path("wishlist/", views.wishlist_view, name="wishlist_view"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"),

    # Cart
    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("cart/move-to-wishlist/<int:item_id>/", views.move_to_wishlist, name="move_to_wishlist"),
    path("cart/move-to-cart/<int:product_id>/", views.move_to_cart, name="move_to_cart"),
    path("cart/get-sizes/<int:product_id>/", views.get_product_sizes, name="get_product_sizes"),

    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/payment/", views.checkout_payment, name="checkout_payment"),

    # Orders (user side)
    path("orders/", views.user_orders, name="user_orders"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/return/", views.request_return, name="return_request"),
]