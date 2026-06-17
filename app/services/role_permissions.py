from sqlalchemy.orm import Session

from app.models import AppPermission, RolePermission, UserRole
from app.permissions import Permission, ROLE_PERMISSIONS, normalize_role_value


def _permission_description(permission: Permission) -> str:
    return permission.value.replace("_", " ").replace(".", " ")


def _ensure_permission_catalog(db: Session) -> dict[str, AppPermission]:
    existing_permissions = {
        item.key: item for item in db.query(AppPermission).all()
    }
    for permission in Permission:
        if permission.value not in existing_permissions:
            permission_row = AppPermission(
                key=permission.value,
                description=_permission_description(permission),
                is_active=True,
            )
            db.add(permission_row)
            existing_permissions[permission.value] = permission_row
    db.flush()
    return {
        item.key: item for item in db.query(AppPermission).all()
    }


def _seed_default_role_permissions(db: Session, permissions_by_key: dict[str, AppPermission]) -> None:
    if db.query(RolePermission).count() > 0:
        return

    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            db.add(RolePermission(
                role=role,
                permission_id=permissions_by_key[permission.value].id,
            ))
    db.flush()


def seed_role_permissions(db: Session) -> None:
    permissions_by_key = _ensure_permission_catalog(db)
    _seed_default_role_permissions(db, permissions_by_key)


def get_role_permission_values(db: Session, role_value) -> tuple[str, ...]:
    role = normalize_role_value(role_value)
    seed_role_permissions(db)
    rows = (
        db.query(AppPermission.key)
        .join(RolePermission, RolePermission.permission_id == AppPermission.id)
        .filter(RolePermission.role == role, AppPermission.is_active == True)
        .order_by(AppPermission.key)
        .all()
    )
    return tuple(row[0] for row in rows)


def list_role_permission_definitions(db: Session, roles: tuple[UserRole, ...]) -> dict[UserRole, tuple[str, ...]]:
    seed_role_permissions(db)
    result: dict[UserRole, tuple[str, ...]] = {}
    for role in roles:
        result[role] = get_role_permission_values(db, role)
    return result


def set_role_permission_values(db: Session, role_value, permission_values: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    role = normalize_role_value(role_value)
    seed_role_permissions(db)

    requested = {str(value).strip() for value in permission_values if str(value).strip()}
    valid_values = {permission.value for permission in Permission}
    invalid = sorted(requested - valid_values)
    if invalid:
        raise ValueError(f"Invalid permissions: {', '.join(invalid)}")

    before = get_role_permission_values(db, role)
    permissions_by_key = {
        item.key: item for item in db.query(AppPermission).filter(AppPermission.key.in_(requested)).all()
    }

    db.query(RolePermission).filter(RolePermission.role == role).delete(synchronize_session=False)
    for permission_key in sorted(requested):
        db.add(RolePermission(
            role=role,
            permission_id=permissions_by_key[permission_key].id,
        ))
    db.flush()
    after = get_role_permission_values(db, role)
    return before, after


INTERVIEW_PERMISSION_KEYS: tuple[str, ...] = (
    "hr.interviews.jobs.manage",
    "hr.interviews.candidates.view",
    "hr.interviews.candidates.manage",
    "hr.interviews.evaluations.review",
    "hr.interviews.candidates.convert",
    "hr.interviews.export",
)


def backfill_interview_role_permissions(db: Session) -> None:
    permissions_by_key = _ensure_permission_catalog(db)

    target_roles = {
        UserRole.HR_MANAGER: INTERVIEW_PERMISSION_KEYS,
        UserRole.ADMIN: INTERVIEW_PERMISSION_KEYS,
    }
    existing_pairs = {
        (normalize_role_value(item.role), item.permission_id)
        for item in db.query(RolePermission).all()
    }

    for role, permission_keys in target_roles.items():
        for permission_key in permission_keys:
            permission_row = permissions_by_key.get(permission_key)
            if permission_row is None:
                continue
            pair = (normalize_role_value(role), permission_row.id)
            if pair in existing_pairs:
                continue
            db.add(RolePermission(role=role, permission_id=permission_row.id))
            existing_pairs.add(pair)

    db.flush()
