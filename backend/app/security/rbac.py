from app.models.enums import UserRole

# Fine-grained permissions checked by FastAPI dependencies.
# Navigation visibility is derived from the same matrix but is never sufficient alone.

PERMISSIONS: dict[str, set[UserRole]] = {
    "patients:read": {
        UserRole.ADMIN,
        UserRole.SOCIAL_WORKER,
        UserRole.DUTY_OFFICER,
    },
    "patients:read_sensitive": {
        UserRole.ADMIN,
        UserRole.SOCIAL_WORKER,
    },
    "patients:write": {
        UserRole.ADMIN,
        UserRole.SOCIAL_WORKER,
    },
    "patients:delete": {UserRole.ADMIN},
    "rooms:read": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
        UserRole.SOCIAL_WORKER,
    },
    "rooms:write": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
    },
    "stays:check_in": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
    },
    "stays:check_out": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
    },
    "waitlist:read": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
        UserRole.SOCIAL_WORKER,
    },
    "waitlist:write": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
        UserRole.SOCIAL_WORKER,
    },
    "donations:read": {UserRole.ADMIN, UserRole.FINANCE},
    "donations:write": {UserRole.ADMIN, UserRole.FINANCE},
    "petty_cash:read": {UserRole.ADMIN, UserRole.FINANCE},
    "petty_cash:write": {UserRole.ADMIN, UserRole.FINANCE},
    "meals:read": {UserRole.ADMIN, UserRole.FINANCE},
    "meals:write": {UserRole.ADMIN, UserRole.FINANCE},
    "reports:occupancy": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
        UserRole.VIEWER,
        UserRole.SOCIAL_WORKER,
    },
    "reports:census": {
        UserRole.ADMIN,
        UserRole.SOCIAL_WORKER,
        UserRole.VIEWER,
    },
    "reports:finance": {UserRole.ADMIN, UserRole.FINANCE, UserRole.VIEWER},
    "reports:admission": {
        UserRole.ADMIN,
        UserRole.SOCIAL_WORKER,
        UserRole.DUTY_OFFICER,
        UserRole.VIEWER,
    },
    "users:manage": {UserRole.ADMIN},
    "audit:read": {UserRole.ADMIN},
    "settings:manage": {UserRole.ADMIN},
    "dashboard:ops": {
        UserRole.ADMIN,
        UserRole.DUTY_OFFICER,
        UserRole.SOCIAL_WORKER,
    },
    "dashboard:finance": {UserRole.ADMIN, UserRole.FINANCE},
    "dashboard:viewer": {UserRole.ADMIN, UserRole.VIEWER},
}


def has_permission(role: UserRole | str, permission: str) -> bool:
    role_value = UserRole(role) if not isinstance(role, UserRole) else role
    allowed = PERMISSIONS.get(permission)
    if allowed is None:
        return False
    return role_value in allowed


def permissions_for(role: UserRole | str) -> list[str]:
    role_value = UserRole(role) if not isinstance(role, UserRole) else role
    return sorted(name for name, roles in PERMISSIONS.items() if role_value in roles)


NAV_ITEMS: list[dict] = [
    {"href": "/dashboard", "label": "Dashboard", "any_of": [
        "dashboard:ops", "dashboard:finance", "dashboard:viewer", "reports:occupancy"
    ]},
    {"href": "/patients", "label": "Patients", "any_of": ["patients:read"]},
    {"href": "/rooms", "label": "Rooms", "any_of": ["rooms:read"]},
    {"href": "/waitlist", "label": "Waiting List", "any_of": ["waitlist:read"]},
    {"href": "/donations", "label": "Donations", "any_of": ["donations:read"]},
    {"href": "/petty-cash", "label": "Petty Cash", "any_of": ["petty_cash:read"]},
    {"href": "/meals", "label": "Meal Sponsorship", "any_of": ["meals:read"]},
    {"href": "/reports", "label": "Reports", "any_of": [
        "reports:occupancy", "reports:census", "reports:finance", "reports:admission"
    ]},
    {"href": "/users", "label": "Users", "any_of": ["users:manage"]},
    {"href": "/audit", "label": "Audit Log", "any_of": ["audit:read"]},
    {"href": "/settings", "label": "Settings", "any_of": ["settings:manage"]},
]


def navigation_for(role: UserRole | str) -> list[dict]:
    granted = set(permissions_for(role))
    items = []
    for item in NAV_ITEMS:
        if any(perm in granted for perm in item["any_of"]):
            items.append({"href": item["href"], "label": item["label"]})
    return items
