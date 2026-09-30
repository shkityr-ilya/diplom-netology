from django.urls import path

from .views import (
    RegisterAccount,
    LoginAccount,
    ConfirmAccount,
    AccountDetail,
    ProductView,
    ProductInfoDetailView,
    CategoryView,
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
]
