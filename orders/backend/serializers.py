from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, Contact, ProductParameter, ProductInfo, Category, Shop

# Сериализатор для входа пользователя


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
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
        return User.objects.create_user(**validated_data)


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


# Сериализатор для контактов


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
            "phone",
        ]


# Сериаизатор для параметров


class ParamsSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="parameter.name")

    class Meta:
        model = ProductParameter
        fields = ["name", "value"]


# Сериализато для информации о продукте


class ProductInfoSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.name")
    catalog = serializers.CharField(source="product.catalog_id")
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


# Сериализато для категории


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


# Сериализато для магазина


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "url"]
