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


def send_interview_candidate_email(
    destination_email: str,
    candidate_name: str,
    template: str,
    context: dict = None
) -> bool:
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        return False

    context = context or {}
    job_title = context.get("job_title", "Position")
    invite_url = context.get("invite_url", "")
    expires_at = context.get("expires_at", "")

    # Format expires_at if it's a datetime object
    if hasattr(expires_at, "strftime"):
        expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Define subject and body for each template
    if template == "interview_invite":
        subject = f"Interview Invitation: {job_title}"
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"You have been invited to interview for the {job_title} position.",
            f"Please click the following link to start your interview: {invite_url}",
            f"This link will expire on {expires_at}.",
            "",
            "Thank you for your interest, and we look forward to hearing your responses.",
        ]
    elif template == "application_received":
        subject = f"Application Received: {job_title}"
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"We have received your application for the {job_title} position.",
            "Our recruitment team will review your application and get back to you soon.",
            "",
            "Thank you for your interest.",
        ]
    elif template == "accepted":
        subject = f"Congratulations! You have been accepted for {job_title}"
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"We are pleased to inform you that you have been accepted for the {job_title} position.",
            "An HR team member will contact you soon with the next steps and onboarding details.",
            "",
            "Congratulations!",
        ]
    elif template == "rejected":
        subject = f"Update on your application for {job_title}"
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"Thank you for your interest in the {job_title} position and for taking the time to apply.",
            "Unfortunately, we will not be moving forward with your application at this time as we search for candidates whose experience closer matches our current needs.",
            "",
            "We wish you all the best in your future endeavors.",
        ]
    elif template == "archived":
        subject = f"Application Status Update: {job_title}"
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"Your application for the {job_title} position has been archived.",
            "We will keep your details on file for future opportunities that align with your profile.",
            "",
            "Thank you for your interest.",
        ]
    elif template == "missing_mcq_reminder":
        subject = f"Reminder: Complete your assessment for {job_title}"
        link_part = f" Please click the following link to complete it: {invite_url}" if invite_url else " Please use your original interview link to access the portal."
        body_lines = [
            f"Hello {candidate_name},",
            "",
            f"This is a reminder to complete your written assessment (MCQ) for the {job_title} position.{link_part}",
            "Please complete it as soon as possible to proceed with your application.",
            "",
            "Thank you.",
        ]
    else:
        raise ValueError(f"Unsupported email template: {template}")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = destination_email
    message.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception:
        return False
