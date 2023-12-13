from enum import StrEnum, auto
from pydantic import BaseModel, validator
from typing import Self


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
    def __new__(cls, value, required, tags):
        value = value.replace("__", ":")
        m = str.__new__(cls, value)
        m._value_ = value

        m._required = required
        if m._required is not None:
            m._required = cls[m._required[0].upper()]

        m._tags = frozenset(tags)

        return m

    @property
    def tags(self) -> frozenset[ScopeTags]:
        return self._tags

    @property
    def required(self) -> Self | None:
        return self._required

    CURI__ADMIN = auto(), None, [ScopeTags.INTERNAL, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ]
    MANTARRAY__ADMIN = auto(), None, [ScopeTags.MANTARRAY, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ]
    MANTARRAY__BASE = auto(), None, [ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE]
    MANTARRAY__RW_ALL_DATA = (
        auto(),
        MANTARRAY__BASE,
        [ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    MANTARRAY__FIRMWARE__GET = auto(), MANTARRAY__BASE, [ScopeTags.MANTARRAY]
    MANTARRAY__FIRMWARE__LIST = auto(), MANTARRAY__BASE, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    MANTARRAY__FIRMWARE__EDIT = auto(), MANTARRAY__FIRMWARE__LIST, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    MANTARRAY__SOFTWARE__EDIT = auto(), None, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    MANTARRAY__SERIAL_NUMBER__LIST = auto(), MANTARRAY__BASE, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    MANTARRAY__SERIAL_NUMBER__EDIT = (
        auto(),
        MANTARRAY__SERIAL_NUMBER__LIST,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    NAUTILUS__ADMIN = auto(), None, [ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.ADMIN]
    NAUTILUS__BASE = auto(), None, [ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE]
    NAUTILUS__RW_ALL_DATA = (
        auto(),
        NAUTILUS__BASE,
        [ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    # TODO need to revisit these. Maybe tag these as UNASSIGNABLE since they will never be in the DB?
    REFRESH = auto(), None, []
    USER__VERIFY = auto(), None, [ScopeTags.ACCOUNT]
    USER__RESET = auto(), None, [ScopeTags.ACCOUNT]
    ADMIN__VERIFY = auto(), None, [ScopeTags.ACCOUNT]
    ADMIN__RESET = auto(), None, [ScopeTags.ACCOUNT]


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


def get_assignable_scopes_from_admin(admin_scopes: list[Scopes]) -> list[Scopes]:
    unassignable_tags = {ScopeTags.ADMIN}
    if Scopes.CURI__ADMIN not in admin_scopes:
        unassignable_tags.add(ScopeTags.INTERNAL)

    product_tags_of_admin = get_product_tags_of_admin(admin_scopes)

    assignable_scopes = []
    for ptag in product_tags_of_admin:
        assignable_scopes_for_product = [
            s for s in Scopes if ptag in s.tags and not (unassignable_tags & s.tags)
        ]
        assignable_scopes += assignable_scopes_for_product

    return assignable_scopes


def get_scope_dependencies(scopes: list[Scopes]) -> dict[Scopes, Scopes]:
    return {s: s.required for s in scopes}


def check_prohibited_scopes(user_scopes: list[Scopes], admin_scopes: list[Scopes]) -> None:
    assignable_scopes = get_assignable_scopes_from_admin(admin_scopes)
    if prohibited_scopes := set(user_scopes) - set(assignable_scopes):
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {prohibited_scopes}")
