from django.urls import path
from .views import (
    login_view,
    logout_view,
    dashboard_view,
    balance_view,
    shop_view,
    cart_view,
    admin_add_product_view,
    admin_currency_view,
    admin_orders_view
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('balance/', balance_view, name='balance'),
    path('shop/', shop_view, name='shop'),
    path('cart/', cart_view, name='cart'),

    # ТРИ НАШИХ СТРАНИЦЫ АДМИНКИ (ПО SOLID)
    path('management/add-product/', admin_add_product_view, name='admin_add_product'),
    path('management/currency/', admin_currency_view, name='admin_currency'),
    path('management/orders/', admin_orders_view, name='admin_orders'),

    path('', dashboard_view, name='dashboard'),
]
