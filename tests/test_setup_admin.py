import pytest

from app.database import SessionLocal
from app.models import Employee, UserRole
from app.security import verify_password
from setup_admin import (
    BOOTSTRAP_ADMIN_CREDENTIAL_ENV,
    BOOTSTRAP_ADMIN_EMAIL,
    get_bootstrap_admin_credential,
    setup_admin,
)


def test_get_bootstrap_admin_credential_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(BOOTSTRAP_ADMIN_CREDENTIAL_ENV, raising=False)

    with pytest.raises(RuntimeError, match=BOOTSTRAP_ADMIN_CREDENTIAL_ENV):
        get_bootstrap_admin_credential()


def test_get_bootstrap_admin_credential_rejects_weak_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(BOOTSTRAP_ADMIN_CREDENTIAL_ENV, "weakpass")

    with pytest.raises(ValueError, match="Password must include"):
        get_bootstrap_admin_credential()


def test_setup_admin_creates_admin_without_logging_raw_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap_credential = "ValidPass1!"
    printed_messages: list[str] = []

    monkeypatch.setenv(BOOTSTRAP_ADMIN_CREDENTIAL_ENV, bootstrap_credential)
    monkeypatch.setattr(
        "builtins.print",
        lambda *args, **kwargs: printed_messages.append(" ".join(str(arg) for arg in args)),
    )

    setup_admin()

    db = SessionLocal()
    try:
        user = db.query(Employee).filter(Employee.email == BOOTSTRAP_ADMIN_EMAIL).one()
        assert user.role == UserRole.ADMIN
        assert user.employee_code == "ADM-001"
        assert user.hashed_password != bootstrap_credential
        assert verify_password(bootstrap_credential, user.hashed_password) is True
    finally:
        db.close()

    combined_output = " ".join(printed_messages)
    assert bootstrap_credential not in combined_output
    assert "admin@voiceqa.ai / password" not in combined_output


def test_setup_admin_upgrades_placeholder_user(monkeypatch: pytest.MonkeyPatch) -> None:
    bootstrap_credential = "StrongPass2!"
    monkeypatch.setenv(BOOTSTRAP_ADMIN_CREDENTIAL_ENV, bootstrap_credential)

    db = SessionLocal()
    try:
        db.add(
            Employee(
                name="Placeholder Admin",
                email="change@me.com",
                hashed_password="legacy-hash",
                role=UserRole.AGENT,
                employee_code="TMP-001",
            )
        )
        db.commit()
    finally:
        db.close()

    setup_admin()

    db = SessionLocal()
    try:
        user = db.query(Employee).filter(Employee.employee_code == "TMP-001").one()
        assert user.email == BOOTSTRAP_ADMIN_EMAIL
        assert user.role == UserRole.ADMIN
        assert verify_password(bootstrap_credential, user.hashed_password) is True
    finally:
        db.close()
