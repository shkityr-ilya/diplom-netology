# Order Service — backend для автоматизации закупок в розничной сети

REST API-сервис на **Django 4 / Django Rest Framework** для заказа товаров у нескольких поставщиков.
Все взаимодействие — через API (Postman / curl), фронтенд не требуется.

## Функциональность

**Покупатель:**
- регистрация с подтверждением по email, вход по токену, восстановление пароля;
- просмотр каталога товаров от нескольких поставщиков с фильтрацией, поиском, сортировкой и пагинацией;
- корзина: добавление/изменение количества/удаление товаров от **разных магазинов в одном заказе**;
- адресная книга контактов доставки;
- подтверждение заказа с проверкой остатков на складе;
- email-подтверждение заказа клиенту и накладная администратору;
- история и детали заказов.

**Поставщик (тип `shop`):**
- импорт прайса из YAML-файла по ссылке;
- включение/отключение приёма заказов;
- список заказов с его товарами *(эндпоинт ниже в roadmap)*.

**Администратор:**
- смена статуса заказа (`new → confirmed → assembled → sent → delivered / canceled`).

## Технологии

- Python >= 3.10, Django, Django Rest Framework
- Токен-аутентификация (`rest_framework.authtoken`)
- django-filter, SearchFilter / OrderingFilter, LimitOffsetPagination
- PyYAML (импорт прайса), requests
- django-rest-passwordreset (токены подтверждения email)
- SQLite (разработка) / PostgreSQL (прод)

## Структура проекта

```
orders/                  # конфигурация Django (settings, urls, wsgi)
backend/
├── models.py            # User, Shop, Category, Product, ProductInfo,
│                        # Parameter, ProductParameter, Contact,
│                        # Order, OrderItem, ConfirmEmailToken
├── serializers.py       # сериализаторы всех сущностей
├── views.py             # APIViews / generics-классы
├── urls.py              # маршруты API
└── utils.py             # отправка email (send_email, накладная, письмо клиенту)
requirements.txt
manage.py
```

## Установка и запуск

```bash
git clone <url репозитория>
cd <проект>

python -m venv env
source env/bin/activate        # Windows: env\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # вход по email

python manage.py runserver
```

Сервис доступен по адресу `http://127.0.0.1:8000/`.

## Настройка email

В `settings.py` (для отладки письма печатаются в консоль сервера):

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Прод:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_HOST_USER = '...'
# EMAIL_HOST_PASSWORD = '...'   # app-password
# EMAIL_USE_TLS = True
```

Понадобится также `AUTH_USER_MODEL = 'backend.User'` и `rest_framework.authtoken` в `INSTALLED_APPS`.

## Аутентификация

Token-based: заголовок `Authorization: Token <ключ>` для защищённых эндпоинтов.
Токен выдаётся при входе (`/login/`).

## Эндпоинты API

### Пользователи

| Метод | URL | Описание | Тело запроса |
|---|---|---|---|
| POST | `/api/register/` | Регистрация; письмо с токеном на email | `first_name, last_name, email, password, confirm_password` |
| POST | `/api/user/confirm/` | Подтверждение аккаунта | `email, token` |
| POST | `/api/login/` | Вход, выдача токена | `email, password` |
| GET/POST | `/api/user/details/` | Профиль пользователя (чтение/изменение) | — |


### Каталог

| Метод | URL | Описание | Query-параметры |
|---|---|---|---|
| GET | `/api/products/` | Список товаров (только активные магазины) | `shop_id`, `product__category_id`, `price__gte/lte`, `quantity__gt`, `search` (по названию и модели), `ordering=price/quantity`, `limit`, `offset` |
| GET | `/api/product/<int:pk>/` | Карточка товара с характеристиками | — |
| GET | `/api/categories/` | Список категорий | — |
| GET | `/api/shops/` | Список магазинов | — |

JSON товара: `id, product (наименование), catalog, shop (поставщик), description (модель), price, price_rrc, quantity, product_parameters [{name, value}]`.

### Корзина

| Метод | URL | Описание | Тело запроса |
|---|---|---|---|
| GET | `/api/basket/` | Содержимое корзины с суммами | — |
| POST/PUT | `/api/basket/` | Добавить/обновить позиции (товары разных магазинов в одном заказе) | `{"items": [{"product_info_id": 1, "quantity": 2}]}` |
| DELETE | `/api/basket/` | Удалить позиции | `{"items": [{"product_info_id": 1}]}` |

### Контакты

| Метод | URL | Описание |
|---|---|---|
| GET/POST | `/api/user/contact/` | Список / создание адреса доставки |
| GET/PUT/PATCH/DELETE | `/api/user/contact/<int:pk>/` | Чтение / изменение / удаление контакта |

Поля: `last_name, first_name, patronymic, email, phone, city, street, house, structure, building, apartment`.

### Заказы

| Метод | URL | Описание | Тело запроса |
|---|---|---|---|
| POST | `/api/order/` | Подтверждение корзины: проверка остатков, списание со склада, статус `new`, письма клиенту и админу | `{"id": <id корзины>, "contact": <id контакта>}` |
| GET | `/api/orders/` | История заказов | — |
| GET | `/api/order/<id>/` | Детали заказа (позиции, суммы, контакт) | — |
| POST | `/api/admin/order/<id>/` | Смена статуса (только администратор) | `{"state": "confirmed"}` |

Статусы: `basket, new, confirmed, assembled, sent, delivered, canceled`.

### Поставщик

| Метод | URL | Описание | Тело запроса |
|---|---|---|---|
| POST | `/api/partner/update/` | Импорт прайса из YAML (только `type=shop`) | `{"url": "https://.../shop1.yaml"}` |

## Сценарий использования (end-to-end)

1. `POST /api/register/` — регистрация, на почту приходит токен.
2. `POST /api/user/confirm/` — активация аккаунта.
3. `POST /api/login/` — получение токена.
4. `GET /api/products/` → `GET /api/product/<int:pk>/` — выбор товаров разных магазинов.
5. `POST /api/basket/` — добавление в корзину.
6. `POST /api/user/contact/` — адрес доставки.
7. `POST /api/order/` — подтверждение: остатки проверены, письма отправлены.
8. `GET /api/orders/` → `GET /api/order/<id>/` — история и детали заказа.

### Поставщику

1. Создать пользователя типа `shop`: в админке или `python manage.py shell`:
   ```python
   from backend.models import User
   u = User.objects.create_user(email='shop@mail.ru', password='...', is_active=True)
   u.type = 'shop'; u.save()
   ```
2. `POST /api/v1/partner/update/` с `url` на YAML-прайс, например из репозитория курса (файл `shop1.yaml`).

## Тестирование

```bash
python manage.py test
# или curl-ом:
curl -X POST http://127.0.0.1:8000/api/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@mail.ru", "password": "pass"}'
```

## Roadmap

- [ ] `/partner/state/` — включение/отключение приёма заказов магазином
- [ ] `/partner/orders/` — список заказов поставщика (товары из его прайса)
- [ ] Swagger-схема через drf-yasg

# ![Описание изображения](/orders/img/python.jpg)