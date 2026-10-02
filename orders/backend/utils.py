from django.core.mail import EmailMessage


def send_email(subject, message, recipients, attachement=None):
    email = EmailMessage(subject=subject, body=message, to=recipients)
    if attachement:
        email.attach_file(*attachement)
        email.send()
