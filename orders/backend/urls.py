from django.urls import path

from .views import RegisterAccount, LoginAccount, ConfirmAccount, AccountDetail

urlpatterns = [
    path("register/", RegisterAccount.as_view(), name="register"),  # регистрация
    path("login/", LoginAccount.as_view(), name="login"),  # вход
    path(
        "user/confirm/", ConfirmAccount.as_view(), name="confirm"
    ),  # подтверждение по email
    path(
        "user/details/", AccountDetail.as_view(), name="details"
    ),  # детальная ин-ция о пользователе
]
