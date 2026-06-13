import smtplib
from email.message import EmailMessage

from app.config import get_settings


def send_login_otp_email(destination_email: str, employee_name: str, otp_code: str) -> bool:
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        return False

    message = EmailMessage()
    message["Subject"] = "Your VoiceQA login code"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = destination_email
    message.set_content(
        "\n".join(
            [
                f"Hello {employee_name},",
                "",
                f"Your login verification code is: {otp_code}",
                "",
                f"This code expires in {settings.LOGIN_OTP_EXPIRE_MINUTES} minutes.",
                "If you did not try to sign in, please contact your administrator.",
            ]
        )
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
    return True


def send_password_reset_otp_email(destination_email: str, employee_name: str, otp_code: str) -> bool:
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        return False

    message = EmailMessage()
    message["Subject"] = "Your VoiceQA password reset code"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = destination_email
    message.set_content(
        "\n".join(
            [
                f"Hello {employee_name},",
                "",
                f"Your password reset verification code is: {otp_code}",
                "",
                f"This code expires in {settings.LOGIN_OTP_EXPIRE_MINUTES} minutes.",
                "If you did not request a password reset, please contact your administrator immediately.",
            ]
        )
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
    return True
