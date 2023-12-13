from enum import StrEnum, auto
from pydantic import BaseModel, validator


class ProhibitedScopeError(Exception):
    pass


class ProhibitedProductError(Exception):
    pass


class ScopeTags(StrEnum):
    INTERNAL = auto()  # TODO rename this to production?
    MANTARRAY = auto()
    NAUTILUS = auto()
    ADMIN = auto()
    PULSE3D_READ = auto()
    PULSE3D_WRITE = auto()
    ACCOUNT = (  # TODO might want to come up with a better name for this since there are other account related things and this could become confusing
        auto()
    )


class Scopes(StrEnum):
    def __new__(cls, value, *tags):
        value = value.replace("__", ":")
        m = str.__new__(cls, value)
        m._value_ = value

        tags = frozenset(tags)

        # TODO use a property here so that the tags attr is immutable?
        m.tags = tags
        return m

    CURI__ADMIN = auto(), ScopeTags.INTERNAL, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ
    MANTARRAY__ADMIN = auto(), ScopeTags.MANTARRAY, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ
    MANTARRAY__RW_ALL_DATA = auto(), ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE
    MANTARRAY__BASE = (auto(), ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE)
    MANTARRAY__FIRMWARE__GET = auto(), ScopeTags.MANTARRAY
    MANTARRAY__FIRMWARE__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__FIRMWARE__LIST = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__SOFTWARE__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__SERIAL_NUMBER__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__SERIAL_NUMBER__LIST = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    NAUTILUS__ADMIN = auto(), ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.ADMIN
    NAUTILUS__RW_ALL_DATA = auto(), ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE
    NAUTILUS__BASE = (auto(), ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE)
    # TODO need to revisit these. Maybe tag these as UNASSIGNABLE since they will never be in the DB?
    REFRESH = auto()
    USER__VERIFY = auto(), ScopeTags.ACCOUNT
    USER__RESET = auto(), ScopeTags.ACCOUNT
    ADMIN__VERIFY = auto(), ScopeTags.ACCOUNT
    ADMIN__RESET = auto(), ScopeTags.ACCOUNT


class ScopeConverter(BaseModel):
    @validator("scopes", check_fields=False)
    def convert_scopes(cls, scopes):
        if scopes is None:
            return None

        return [convert_scope_str(s) for s in scopes]


def convert_scope_str(scope_str: str) -> Scopes:
    return Scopes[scope_str.upper().replace(":", "__")]


# TODO add testing for these
def get_product_tags_of_admin(admin_scopes) -> set[Scopes]:
    return {tag for s in admin_scopes for tag in s.tags if ScopeTags.ADMIN in s.tags} & {
        ScopeTags.MANTARRAY,
        ScopeTags.NAUTILUS,
    }


def check_prohibited_product(user_scopes, product) -> None:
    if not [s for s in user_scopes if product in s.tags]:
        raise ProhibitedProductError(product)


def get_assignable_scopes_from_admin(admin_scopes) -> dict[str, list[str]]:
    unassignable_tags = {ScopeTags.ADMIN}
    if Scopes.CURI__ADMIN not in admin_scopes:
        unassignable_tags.add(ScopeTags.INTERNAL)

    product_tags_of_admin = get_product_tags_of_admin(admin_scopes)

    assignable_scopes = {}
    for ptag in product_tags_of_admin:
        assignable_scopes_for_product = [
            s for s in Scopes if ptag in s.tags and not (unassignable_tags & s.tags)
        ]
        assignable_scopes[ptag.name.lower()] = assignable_scopes_for_product

    return assignable_scopes


def check_prohibited_scopes(user_scopes, admin_scopes) -> None:
    assignable_scopes_by_product = get_assignable_scopes_from_admin(admin_scopes)
    assignable_scopes = set(
        s for product_scopes in assignable_scopes_by_product.values() for s in product_scopes
    )
    if prohibited_scopes := set(user_scopes) - assignable_scopes:
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {prohibited_scopes}")
