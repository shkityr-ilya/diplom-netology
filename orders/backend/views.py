from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from requests import get
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml import Loader
from yaml import load as load_yaml

from .models import (
    Category,
    ConfirmEmailToken,
    Contact,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
)
from .serializers import (
    AddBasketSerializer,
    BasketSerializer,
    CategorySerializer,
    ContactSerializer,
    LoginSerializer,
    OrderConfirmSerializer,
    OrderDetailSerializer,
    OrderStateSerializer,
    ProductInfoSerializer,
    RegisterSerializer,
    ShopSerializer,
    UserSerializer,
)
from .utils import send_admin_invoice, send_client_email, send_email

User = get_user_model()


# API для регистрации пользователя


class RegisterAccount(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = ConfirmEmailToken.objects.update_or_create(
                user=user, key=ConfirmEmailToken.generate_key()
            )
            send_email(
                subject="Подтверждение аккаунта",
                message=f"Для подтверждения аккаунта перейдите по ссылке: {token.key}",
                recipients=[user.email],
            )
            return Response(
                {
                    "Status": "OK",
                    "detail": "Письмо с подтверждением отправлено на вашу почту",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Status": "Error", "Error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# API для подтверждения аккаунта


class ConfirmAccount(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        token = request.data.get("token")
        if not email or not token:
            return Response(
                {"Status": "Error", "detail": "Не передан email или токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(email=email)
            token = ConfirmEmailToken.objects.get(user=user, key=token)
        except (User.DoesNotExist, ConfirmEmailToken.DoesNotExist):
            return Response(
                {"Status": "Error", "detail": "Пользователь не найден"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        token.delete()
        return Response(
            {"Status": "OK", "detail": "Аккаунт подтвержден"}, status=status.HTTP_200_OK
        )


# API для входа пользователя


class LoginAccount(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"Status": "OK", "Token": token.key})
        return Response(
            {"Status": "Error", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# API для детальной информации пользователя (изменение данных профиля)


class AccountDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            send_email(
                subject="Изменение данных профиля",
                message=f"Данные вашего профиля были изменены. Новые данные: {serializer.data}",
                recipients=[request.user.email],
            )
            return Response(serializer.data)
        return Response(
            {"Status": "Error", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def send_email(self, subject, message, recipients, attachment=None):

        email = EmailMessage(subject=subject, body=message, to=recipients)
        if attachment:
            email.attach(*attachment)
        email.send()


# API для списка продуктов + фильтрация, сортировка, поиск, пагинация


class ProductView(ListAPIView):
    queryset = (
        ProductInfo.objects.select_related("product", "shop", "product__category")
        .prefetch_related("product_parameters__parameter")
        .filter(shop__state=True)
    )
    serializer_class = ProductInfoSerializer
    permission_classes = [AllowAny]
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "shop_id": ["exact"],
        "product__category_id": ["exact"],
        "price": ["gte", "lte"],
        "quantity": ["gt"],
    }
    search_fields = ["product__name", "model"]
    ordering_fields = ["price", "quantity"]


# API для получения информации по отдельному товару


class ProductInfoDetailView(RetrieveAPIView):
    queryset = ProductInfo.objects.select_related(
        "product", "shop", "product__category"
    ).prefetch_related("product_parameters__parameter")
    serializer_class = ProductInfoSerializer
    permission_classes = [AllowAny]


# API для списка категорий


class CategoryView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


# API для списка магазинов


class ShopView(ListAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [AllowAny]


# API для корзины


class BasketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        basket, _ = (
            Order.objects.select_related("user")
            .prefetch_related(
                Prefetch(
                    "ordered_items",
                    queryset=OrderItem.objects.select_related(
                        "product_info__product", "product_info__shop"
                    ),
                )
            )
            .get_or_create(user=request.user, state="basket")
        )
        serializer = BasketSerializer(basket, context={"request": request})
        return Response({"status": "OK", "data": serializer.data})

    def post(self, request, *args, **kwargs):
        serializer = AddBasketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "Error", "detail": serializer.errors}, status=400
            )
        basket, _ = Order.objects.get_or_create(user=request.user, state="basket")
        items_data = serializer.validated_data["items"]
        errors = {}
        created_count = 0
        with transaction.atomic():
            for item in items_data:
                try:
                    info = ProductInfo.objects.select_related("shop").get(
                        pk=item["product_info_id"], shop__state=True
                    )
                except ProductInfo.DoesNotExist:
                    errors[item["product_info_id"]] = (
                        "Товар не найден или магазин не принимает заказы"
                    )
                    continue
                obj, created_flag = OrderItem.objects.update_or_create(
                    order=basket,
                    product_info=info,
                    defaults={"quantity": item["quantity"]},
                )

                if created_flag:
                    created_count += 1
        if errors:
            return Response(
                {
                    "status": "OK (with errors)",
                    "created": created_count,
                    "errors": errors,
                },
                status=400,
            )
        return Response(
            {"status": "OK", "created": created_count, "errors": errors}, status=201
        )

    def put(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        serializer = AddBasketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "Error", "detail": serializer.errors}, status=400
            )
        basket, _ = Order.objects.get_or_create(user=request.user, state="basket")
        items_ids = [
            item["product_info_id"] for item in serializer.validated_data["items"]
        ]
        queryset = OrderItem.objects.filter(order=basket, product_info_id__in=items_ids)
        deleted_count, _ = queryset.delete()
        return Response({"status": "OK", "deleted": deleted_count}, status=200)


# API для добавления/удаления адреса доставки


class ContactListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)


# API для подтверждения заказа


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = OrderConfirmSerializer(
            data=request.data, context={"request": request}
        )

        with transaction.atomic():
            serializer.is_valid(raise_exception=True)
            confirmed_order = serializer.save()
            transaction.on_commit(
                lambda: (
                    send_client_email(request.user, confirmed_order),
                    send_admin_invoice(confirmed_order),
                )
            )
        response_serializer = OrderDetailSerializer(confirmed_order)
        return Response(
            {
                "status": "OK",
                "detail": f"Заказ №{confirmed_order.id} подтверждён.",
                "total": confirmed_order.total,
                "data": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# API для получения списка заказов


class OrderListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .exclude(state="basket")
            .select_related("contact")
            .prefetch_related(
                "ordered_items__product_info__product",
                "ordered_items__product_info__shop",
            )
        )


class OrderDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .exclude(state="basket")
            .select_related("contact")
            .prefetch_related(
                "ordered_items__product_info__product",
                "ordered_items__product_info__shop",
            )
        )


# API для редактирования статуса заказа


class OrderStateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"Status": False, "Errors": "Только для администратора"}, status=403
            )
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderStateSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"Status": True, "data": serializer.data})
        return Response({"Status": False, "Errors": serializer.errors}, status=400)


# API для импорта товаров


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        url = request.data.get("url")
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({"Status": False, "Error": str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(
                    name=data["shop"], user_id=request.user.id
                )
                for category in data["categories"]:
                    category_object, _ = Category.objects.get_or_create(
                        id=category["id"], name=category["name"]
                    )
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data["goods"]:
                    product, _ = Product.objects.get_or_create(
                        name=item["name"], category_id=item["category"]
                    )

                    product_info = ProductInfo.objects.create(
                        product_id=product.id,
                        external_id=item["id"],
                        model=item["model"],
                        price=item["price"],
                        price_rrc=item["price_rrc"],
                        quantity=item["quantity"],
                        shop_id=shop.id,
                    )
                    for name, value in item["parameters"].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info_id=product_info.id,
                            parameter_id=parameter_object.id,
                            value=value,
                        )

                return JsonResponse({"Status": True})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )
