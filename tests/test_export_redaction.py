from app.routers.export import redact_text, redact_transcript
from app.models import UserRole


def test_redact_text_contract_patterns():
    text = (
        "Customer DOB 01/02/1990, account number ACCT-12345, customer id CUST-777, "
        "transcript id T-999, session #ABC-123, call id CALL-321."
    )
    redacted = redact_text(text)

    assert "[DOB_REDACTED]" in redacted
    assert "[ACCOUNT_ID_REDACTED]" in redacted
    assert "[CUSTOMER_ID_REDACTED]" in redacted
    assert "[TRANSCRIPT_ID_REDACTED]" in redacted


def test_redact_transcript_list_objects():
    transcript = [
        {"speaker": "Agent", "text": "Email me at agent@example.com and call 123-456-7890."},
        {"speaker": "Customer", "text": "DOB 1990-02-01 and customer number 998877."},
    ]

    redacted = redact_transcript(transcript, UserRole.QA)

    assert "[EMAIL_REDACTED]" in redacted[0]["text"]
    assert "[PHONE_REDACTED]" in redacted[0]["text"]
    assert "[DOB_REDACTED]" in redacted[1]["text"]
    assert "[CUSTOMER_ID_REDACTED]" in redacted[1]["text"]


def test_admin_redaction_bypass():
    transcript = [{"speaker": "Agent", "text": "agent@example.com"}]
    assert redact_transcript(transcript, UserRole.ADMIN) == transcript
