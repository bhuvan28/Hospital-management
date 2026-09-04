from enum import Enum


class UserRole(str, Enum):
    DUTY_OFFICER = "duty_officer"
    SOCIAL_WORKER = "social_worker"
    ADMIN = "admin"
    FINANCE = "finance"
    VIEWER = "viewer"


class PatientStatus(str, Enum):
    NEW = "new"
    RETURNING = "returning"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class RoomStatus(str, Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class DonationType(str, Enum):
    CASH = "cash"
    IN_KIND = "in_kind"
    EVENT = "event"
    CORPORATE = "corporate"
    RMH_FAMILY = "rmh_family"
    VOLUNTEER = "volunteer"


class PettyCashCategory(str, Enum):
    GROCERIES = "groceries"
    STATIONERY_OFFICE = "stationery_office"
    KITCHEN_LAUNDRY = "kitchen_laundry"
    OTHER = "other"
    MAINTENANCE_REPAIR = "maintenance_repair"


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    HI_TEA = "hi_tea"
    DINNER = "dinner"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    RESOLVE = "resolve"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
