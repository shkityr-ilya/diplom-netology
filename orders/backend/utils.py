import csv
from io import StringIO

from django.conf import settings
from django.core.mail import EmailMessage, send_mail


def send_email(subject, message, recipients, attachement=None):
    email = EmailMessage(subject=subject, body=message, to=recipients)
    if attachement:
        email.attach_file(*attachement)
        email.send()


def get_contact_address(order):
    contact = order.contact
    address_parts = [
        f"{contact.city}" if hasattr(contact, "city") else "",
        f"улица {contact.street}" if hasattr(contact, "street") else "",
        f"дом {contact.house}" if hasattr(contact, "house") else "",
        (
            f"строение {contact.building}"
            if hasattr(contact, "building") and contact.building
            else ""
        ),
        (
            f"квавтира {contact.apartment}"
            if hasattr(contact, "apartment") and contact.apartment
            else ""
        ),
    ]
    return ", ".join(part for part in address_parts if part)


def send_client_email(user, order):
    items = order.ordered_items.select_related(
        "product_info__product", "product_info__shop"
    )
    rows = "\n".join(
        f"- {i.product_info.product.name} ({i.product_info.shop.name}) "
        f"× {i.quantity} шт. = {i.product_info.price * i.quantity:,.2f} руб."
        for i in items
    )
    total = sum(i.product_info.price * i.quantity for i in items)
    subject = f"Ваш заказ №{order.id} подтверждён"
    message = (
        f"Уважаемый(-ая) {user.first_name or 'Клиент'}!\n\n"
        f"Тема: Подтверждение заказа №{order.id}\n\n"
        f"Состав вашего заказа:\n{rows}\n\n"
        f"Итого к оплате: {total:,.2f} руб.\n"
        f"Пожалуйста, проверьте данные доставки:\n{get_contact_address(order)}\n\n"
        f"Мы свяжемся с вами по телефону {order.contact.phone}.\n"
        f"Благодарим за покупку!"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_admin_invoice(order):
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["№", "Товар", "Магазин", "Цена", "Кол-во", "Сумма"])
    for item in order.ordered_items.select_related(
        "product_info__product", "product_info__shop"
    ):
        writer.writerow(
            [
                item.product_info.external_id,
                item.product_info.product.name[:30],
                item.product_info.shop.name,
                item.product_info.price,
                item.quantity,
                item.product_info.price * item.quantity,
            ]
        )
    filename = f"invoice_{order.id}.csv"
    attachment = (filename, buffer.getvalue().encode("utf-8"), "text/csv")
    message = (
        f"Добрый день!\n\n"
        f"К вам поступил новый заказ №{order.id} от {order.dt.strftime('%d.%m.%Y')}.\n"
        f"Детали заказа во вложении CSV-файла.\n"
        f"Контакт клиента: тел. {order.contact.phone}, email {order.user.email}.\n"
        f"Адрес доставки: {get_contact_address(order)}"
    )
    send_mail(
        subject=f"Заказ №{order.id}: накладная для магазина",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=False,
        attachments=[attachment],
    )
