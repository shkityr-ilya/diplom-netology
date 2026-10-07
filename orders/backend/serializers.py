import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import F, Sum
from django.db.utils import IntegrityError
from rest_framework import serializers

from .models import (
    Category,
    Contact,
    Order,
    OrderItem,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)

# Сериализатор для входа пользователя


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Неверный email или пароль")
        if not user.is_active:
            raise serializers.ValidationError(
                "Аккаунт не активирован, подтвердите через email"
            )
        attrs["user"] = user
        return attrs


# Сериализатор для регистрации пользователя


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password", "confirm_password"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        validated_data["type"] = "buyer"
        with transaction.atomic():
            try:
                user = User.objects.create(**validated_data)
                user.set_password(password)
                user.save()
                return user
            except IntegrityError:
                raise serializers.ValidationError(
                    {"email": "Пользователь с таким email уже существует"}
                )


# Сериализатор для пользователя


class UserSerializer(serializers.ModelSerializer):
    contacts = serializers.SerializerMethodField(read_only=True)

    def get_contacts(self, obj):
        return [
            {
                "id": contact.id,
                "city": contact.city,
                "street": contact.street,
                "phone": contact.phone,
            }
            for contact in obj.contacts.all()
        ]

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "company",
            "position",
            "type",
            "contacts",
        ]
        read_only_fields = ["id", "email", "type"]


# Сериаизатор для параметров


class ParamsSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="parameter.name")

    class Meta:
        model = ProductParameter
        fields = ["name", "value"]


# Сериализатор для информации о продукте


class ProductInfoSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.name")
    catalog = serializers.CharField(source="product.category_id")
    shop = serializers.CharField(source="shop.name")
    description = serializers.CharField(source="model")
    price = serializers.IntegerField()
    price_rrc = serializers.IntegerField()
    quantity = serializers.IntegerField()
    product_parameters = ParamsSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = [
            "id",
            "product",
            "catalog",
            "shop",
            "description",
            "price",
            "price_rrc",
            "quantity",
            "product_parameters",
        ]


# Сериализатор для категории


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


# Сериализатор для магазина


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "url"]


# Сериализатор для работы с корзиной


class BasketItemInputSerializer(serializers.Serializer):
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class BasketItemSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product_info.product.name", read_only=True)
    shop = serializers.CharField(source="product_info.shop.name", read_only=True)
    price = serializers.IntegerField(source="product_info.price", read_only=True)
    sum = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "product", "shop", "price", "quantity", "sum")

    def get_sum(self, obj):
        return obj.quantity * obj.product_info.price


class BasketSerializer(serializers.ModelSerializer):
    order_items = BasketItemSerializer(
        source="ordered_items", many=True, read_only=True
    )
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "order_items", "total")

    def get_total(self, obj):
        return sum(
            item.product_info.price * item.quantity for item in obj.ordered_items.all()
        )


class AddBasketSerializer(serializers.Serializer):
    items = BasketItemInputSerializer(many=True)


# Сериализатор для адреса доставки


class ContactSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        required=True, validators=[], help_text="Формат: +7 (999) 123-45-67"
    )

    class Meta:
        model = Contact
        fields = [
            "id",
            "last_name",
            "first_name",
            "patronymic",
            "email",
            "phone",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "email": {"required": True},
            "street": {"required": True},
        }

    def validate_phone(self, value):
        if not re.fullmatch(r"[0-9+()\-\s]{5,20}", value):
            raise serializers.ValidationError("Некорректный номер телефона.")
        return value


# Сериализатор для подтверждения заказа


class OrderConfirmSerializer(serializers.Serializer):
    id = serializers.IntegerField(write_only=True)  # Входящий ID заказа
    contact = serializers.IntegerField(write_only=True)  # Входящий ID контакта
    order_id = serializers.IntegerField(source="id", read_only=True)
    state = serializers.CharField(read_only=True)
    dt = serializers.DateTimeField(read_only=True)
    total = serializers.SerializerMethodField()
    contact_data = serializers.SerializerMethodField()

    class Meta:
        fields = ["id", "contact", "order_id", "state", "dt", "total", "contact_data"]

    def get_total(self, obj):
        return getattr(obj, "total", None)

    def get_contact_data(self, obj):
        contact = getattr(obj, "contact_obj", None)
        if contact:
            return ContactSerializer(contact).data
        return None

    def validate(self, attrs):
        user = self.context["request"].user
        order_id = attrs.get("id")
        contact_id = attrs.get("contact")
        try:
            self.instance = (
                Order.objects.select_for_update()
                .filter(pk=order_id, user=user, state="basket")
                .annotate(
                    total=Sum(
                        F("ordered_items__quantity")
                        * F("ordered_items__product_info__price")
                    )
                )
                .first()
            )
            if not self.instance:
                raise serializers.ValidationError(
                    {"id": "Заказ не найден или не в состоянии 'basket'."}
                )
        except Exception as e:
            raise serializers.ValidationError({"id": str(e)})
        try:
            self.contact_obj = Contact.objects.get(pk=contact_id, user=user)
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"contact": "Контакт не найден."})
        return attrs

    def save(self, **kwargs):
        instance = self.instance
        contact_obj = self.contact_obj
        errors = []
        for item in instance.ordered_items.all():
            info = item.product_info
            shop = info.shop
            if not shop.state:
                errors.append(f"Магазин «{shop.name}» временно недоступен.")
            elif info.quantity < item.quantity:
                errors.append(
                    f"Товара «{info.product.name} ({info.model})» осталось всего {info.quantity}"
                )
        if errors:
            raise serializers.ValidationError({"non_field_errors": "\n".join(errors)})
        for item in instance.ordered_items.all():
            info = item.product_info
            info.quantity = max(info.quantity - item.quantity, 0)
            info.save(update_fields=["quantity"])
        instance.state = "new"
        instance.contact = contact_obj
        instance.save(update_fields=["state", "contact"])
        return instance


# Сериализатор для деталей о заказе


class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = BasketItemSerializer(
        source="ordered_items", many=True, read_only=True
    )
    total_sum = serializers.SerializerMethodField()
    contact_data = ContactSerializer(source="contact", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "dt", "state", "order_items", "total_sum", "contact_data"]

    def get_total_sum(self, obj):
        result = (
            getattr(obj, "total_sum", None)
            or obj.ordered_items.aggregate(
                total=Sum(F("quantity") * F("product_info__price"))
            )["total"]
        )
        return result or 0


# Сериализатор для редактирование статуса заказа


class OrderStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("state",)
