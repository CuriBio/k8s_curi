from enum import StrEnum, auto
from pydantic import BaseModel, field_validator
from typing import Self


class ProhibitedScopeError(Exception):
    pass


class ProhibitedProductError(Exception):
    pass


class MissingScopeDependencyError(Exception):
    pass


class ScopeTags(StrEnum):
    INTERNAL = auto()  # TODO rename this to production?
    MANTARRAY = auto()
    NAUTILAI = auto()
    ADMIN = auto()
    PULSE3D_READ = auto()
    PULSE3D_WRITE = auto()
    ADVANCED_ANALYSIS = auto()
    ADVANCED_ANALYSIS_READ = auto()
    ADVANCED_ANALYSIS_WRITE = auto()
    ACCOUNT = (
        # TODO might want to come up with a better name for this since there are other account related things and this could become confusing.
        # maybe EMAIL since these tokens are currently only used in emails?
        auto()
    )
    UNASSIGNABLE = auto()


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

    CURI__ADMIN = (
        auto(),
        None,
        # TODO does this scope really need to be tagged with ScopeTags.PULSE3D_READ? Or should the root account just be assigned every admin scope
        [ScopeTags.INTERNAL, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ, ScopeTags.UNASSIGNABLE],
    )
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
    MANTARRAY__SOFTWARE__EDIT = (
        auto(),
        None,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL, ScopeTags.UNASSIGNABLE],
    )
    MANTARRAY__SERIAL_NUMBER__LIST = auto(), MANTARRAY__BASE, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    MANTARRAY__SERIAL_NUMBER__EDIT = (
        auto(),
        MANTARRAY__SERIAL_NUMBER__LIST,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    MANTARRAY__NMJ = auto(), MANTARRAY__BASE, [ScopeTags.MANTARRAY, ScopeTags.INTERNAL]
    NAUTILAI__ADMIN = auto(), None, [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.ADMIN]
    NAUTILAI__BASE = auto(), None, [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE]
    NAUTILAI__RW_ALL_DATA = (
        auto(),
        NAUTILAI__BASE,
        [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    ADVANCED_ANALYSIS__ADMIN = (
        auto(),
        None,
        [ScopeTags.ADVANCED_ANALYSIS, ScopeTags.ADVANCED_ANALYSIS_READ, ScopeTags.ADMIN],
    )
    ADVANCED_ANALYSIS__BASE = (
        auto(),
        None,
        [ScopeTags.ADVANCED_ANALYSIS, ScopeTags.ADVANCED_ANALYSIS_READ, ScopeTags.ADVANCED_ANALYSIS_WRITE],
    )
    REFRESH = auto(), None, [ScopeTags.UNASSIGNABLE]
    USER__VERIFY = auto(), None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    USER__RESET = auto(), None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    ADMIN__VERIFY = auto(), None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    ADMIN__RESET = auto(), None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]


class ScopeConverter(BaseModel):
    @field_validator("scopes", check_fields=False)
    def convert_scopes(cls, scopes):
        if scopes is None:
            return None

        return [convert_scope_str(s) for s in scopes]


def convert_scope_str(scope_str: str) -> Scopes:
    return Scopes[scope_str.upper().replace(":", "__")]


_PRODUCT_SCOPE_TAGS = frozenset({ScopeTags.MANTARRAY, ScopeTags.NAUTILAI, ScopeTags.ADVANCED_ANALYSIS})


# TODO add testing for these
def get_product_tags_of_admin(admin_scopes: list[Scopes]) -> set[ScopeTags]:
    return {tag for s in admin_scopes for tag in s.tags if ScopeTags.ADMIN in s.tags} & _PRODUCT_SCOPE_TAGS


def get_product_tags_of_user(user_scopes: list[Scopes], rw_all_only: bool = False) -> set[ScopeTags]:
    if rw_all_only:
        user_scopes = [s for s in user_scopes if "rw_all_data" in s]

    return {tag for s in user_scopes for tag in s.tags} & _PRODUCT_SCOPE_TAGS


def check_prohibited_product(user_scopes: list[Scopes], product: str) -> None:
    if not [s for s in user_scopes if product in s.tags]:
        raise ProhibitedProductError(product)


def get_assignable_user_scopes(admin_scopes: list[Scopes]) -> list[Scopes]:
    unassignable_tags = {ScopeTags.ADMIN, ScopeTags.UNASSIGNABLE}
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


def get_assignable_admin_scopes(admin_scopes: list[Scopes]) -> list[Scopes]:
    if Scopes.CURI__ADMIN not in admin_scopes:
        return []

    return [s for s in Scopes if ScopeTags.ADMIN in s.tags and ScopeTags.INTERNAL not in s.tags]


def get_scope_dependencies(scopes: list[Scopes]) -> dict[Scopes, Scopes | None]:
    return {s: s.required for s in scopes}


def validate_scope_dependencies(scopes: list[Scopes]) -> None:
    scope_dependencies = get_scope_dependencies(scopes)
    if missing_scope_deps := {
        scope: required
        for scope, required in scope_dependencies.items()
        if required is not None and required not in scope_dependencies
    }:
        raise MissingScopeDependencyError(str(missing_scope_deps))


def check_prohibited_user_scopes(user_scopes: list[Scopes], admin_scopes: list[Scopes]) -> None:
    assignable_scopes = get_assignable_user_scopes(admin_scopes)
    if prohibited_scopes := set(user_scopes) - set(assignable_scopes):
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {prohibited_scopes}")


def check_prohibited_admin_scopes(other_admin_scopes: list[Scopes], root_admin_scopes: list[Scopes]) -> None:
    assignable_scopes = get_assignable_admin_scopes(root_admin_scopes)
    if prohibited_scopes := set(other_admin_scopes) - set(assignable_scopes):
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {prohibited_scopes}")
    # Tanner (12/14/23): for good measure, double check that the root scope is not present
    if Scopes.CURI__ADMIN in other_admin_scopes:
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {Scopes.CURI__ADMIN}")
