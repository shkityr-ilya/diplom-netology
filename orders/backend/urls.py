from django.urls import path

from .views import (
    AccountDetail,
    BasketView,
    CategoryView,
    ConfirmAccount,
    ContactDetailView,
    ContactListCreateView,
    LoginAccount,
    OrderDetailView,
    OrderListView,
    OrderStateView,
    OrderView,
    ProductInfoDetailView,
    ProductView,
    RegisterAccount,
    ShopView,
)

urlpatterns = [
    path("register/", RegisterAccount.as_view(), name="register"),  # регистрация
    path("login/", LoginAccount.as_view(), name="login"),  # вход
    path(
        "user/confirm/", ConfirmAccount.as_view(), name="confirm"
    ),  # подтверждение по email
    path(
        "user/details/", AccountDetail.as_view(), name="details"
    ),  # детальная ин-ция о пользователе
    path("products/", ProductView.as_view(), name="products"),  # списка продуктов
    path(
        "product/<int:pk>/", ProductInfoDetailView.as_view(), name="product"
    ),  # информация по отдельному товару
    path("categories/", CategoryView.as_view(), name="categories"),  # список категорий
    path("shops/", ShopView.as_view(), name="shops"),  # списка магазинов
    path("basket/", BasketView.as_view(), name="basket"),  # корзина
    path(
        "user/contact/", ContactListCreateView.as_view(), name="user-contact"
    ),  # контакты пользователя
    path(
        "user/contact/<int:pk>/",
        ContactDetailView.as_view(),
        name="user-contact-detail",
    ),
    # детальная инфа о контакте пользователя
    path(
        "order/",
        OrderView.as_view(),
        name="order",
    ),
    # подтверждение заказа
    path(
        "orders/", OrderListView.as_view(), name="order-list"
    ),  # получение списка заказов
    path(
        "order/<int:pk>/", OrderDetailView.as_view(), name="order-detail"
    ),  # получение деталей заказа
    path(
        "admin/order/<int:pk>/", OrderStateView.as_view(), name="admin-order-state"
    ),  # редактирование статуса заказа
]
