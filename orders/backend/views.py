from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import ConfirmEmailToken
from .serializers import LoginSerializer, UserSerializer, RegisterSerializer

# API для регистрации пользователя


class RegisterAccount(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = ConfirmEmailToken.objects.get_or_create(user=user)
            self._send_email(
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

    @staticmethod
    def _send_email(subject, message, recipients, attachment=None):
        from django.core.mail import EmailMessage

        email = EmailMessage(subject=subject, body=message, to=recipients)
        if attachment:
            email.attach(*attachment)
            email.send()


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
            self.send_email(
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
        from django.core.mail import EmailMessage

        email = EmailMessage(subject=subject, body=message, to=recipients)
        if attachment:
            email.attach(*attachment)
        email.send()
