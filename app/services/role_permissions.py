from sqlalchemy.orm import Session

from app.models import AppPermission, RolePermission, UserRole
from app.permissions import Permission, ROLE_PERMISSIONS, normalize_role_value


def _permission_description(permission: Permission) -> str:
    return permission.value.replace("_", " ").replace(".", " ")


def seed_role_permissions(db: Session) -> None:
    existing_permissions = {
        item.key: item for item in db.query(AppPermission).all()
    }
    for permission in Permission:
        if permission.value not in existing_permissions:
            db.add(AppPermission(
                key=permission.value,
                description=_permission_description(permission),
                is_active=True,
            ))
    db.flush()

    if db.query(RolePermission).count() > 0:
        return

    permissions_by_key = {
        item.key: item for item in db.query(AppPermission).all()
    }
    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            db.add(RolePermission(
                role=role,
                permission_id=permissions_by_key[permission.value].id,
            ))
    db.flush()


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
