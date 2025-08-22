from enum import StrEnum, auto
from pydantic import BaseModel, field_validator
from typing import Self, Any


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
    PRODUCT_FEATURE = auto()
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
    def __new__(
        cls,
        value: str,
        required_admin: Self | Any | None,
        prerequisite: Self | Any | None,
        tags: list[ScopeTags],
        inheritable: list[Self | Any] | None = None,
    ):
        """
        Args:
            - value: the name of the scope, should contain __ instead of :
            - required_admin: the scope that an admin account must have in order to assign this scope to one
                of its users
            - prerequisite: the scope that the user must have assigned to it in order to have this scope
                assign to it
            - tags: scope tags of this scopes
        """
        value = value.replace("__", ":")
        m = str.__new__(cls, value)
        m._value_ = value

        m._required_admin = required_admin
        if m._required_admin is not None:
            m._required_admin = cls[m._required_admin[0].upper()]
            if not m._required_admin.is_admin_scope():
                raise ValueError(f"{m._required_admin} is not an admin scope")

        m._prerequisite = prerequisite
        if m._prerequisite is not None:
            m._prerequisite = cls[m._prerequisite[0].upper()]
            if not m._required_admin.is_admin_scope():
                raise ValueError(f"{m._required_admin} is not an admin scope")

        m._inheritable_scopes = [] if inheritable is None else inheritable
        m._inheritable_scopes = [cls[s[0].upper()] for s in m._inheritable_scopes]

        m._tags = frozenset(tags)

        return m

    @property
    def tags(self) -> frozenset[ScopeTags]:
        return self._tags

    @property
    def prerequisite(self) -> Self | None:
        return self._prerequisite

    @property
    def required_admin(self) -> Self | None:
        return self._required_admin

    @property
    def inheritable_scopes(self) -> list[Self]:
        return self._inheritable_scopes

    CURI__ADMIN = (
        auto(),
        None,
        None,
        # TODO does this scope really need to be tagged with ScopeTags.PULSE3D_READ? Or should the root account just be assigned every admin scope
        [ScopeTags.INTERNAL, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ, ScopeTags.UNASSIGNABLE],
    )
    MANTARRAY__ADMIN = (
        auto(),
        CURI__ADMIN,
        None,
        [ScopeTags.MANTARRAY, ScopeTags.ADMIN, ScopeTags.PULSE3D_READ],
    )
    MANTARRAY__NMJ = (
        auto(),
        None,
        None,
        # unassignable because this will be automatically inherited by a user if the admin has the feature scope
        [ScopeTags.MANTARRAY, ScopeTags.UNASSIGNABLE],
    )
    MANTARRAY__NMJ_FEATURE = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__ADMIN,
        [ScopeTags.MANTARRAY, ScopeTags.ADMIN, ScopeTags.PRODUCT_FEATURE],
        [MANTARRAY__NMJ],
    )
    MANTARRAY__CLS_ALG = (
        auto(),
        None,
        None,
        # unassignable because this will be automatically inherited by a user if the admin has the feature scope
        [ScopeTags.MANTARRAY, ScopeTags.UNASSIGNABLE],
    )
    MANTARRAY__CLS_ALG_FEATURE = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__ADMIN,
        [ScopeTags.MANTARRAY, ScopeTags.ADMIN, ScopeTags.PRODUCT_FEATURE],
        [MANTARRAY__CLS_ALG],
    )
    MANTARRAY__BASE = (
        auto(),
        MANTARRAY__ADMIN,
        None,
        [ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    MANTARRAY__RW_ALL_DATA = (
        auto(),
        MANTARRAY__ADMIN,
        MANTARRAY__BASE,
        [ScopeTags.MANTARRAY, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    MANTARRAY__FIRMWARE__GET = auto(), MANTARRAY__ADMIN, MANTARRAY__BASE, [ScopeTags.MANTARRAY]
    MANTARRAY__FIRMWARE__LIST = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__BASE,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    MANTARRAY__FIRMWARE__EDIT = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__FIRMWARE__LIST,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    MANTARRAY__SOFTWARE__EDIT = (
        auto(),
        None,
        None,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL, ScopeTags.UNASSIGNABLE],
    )
    MANTARRAY__SERIAL_NUMBER__LIST = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__BASE,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    MANTARRAY__SERIAL_NUMBER__EDIT = (
        auto(),
        CURI__ADMIN,
        MANTARRAY__SERIAL_NUMBER__LIST,
        [ScopeTags.MANTARRAY, ScopeTags.INTERNAL],
    )
    NAUTILAI__ADMIN = auto(), CURI__ADMIN, None, [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.ADMIN]
    NAUTILAI__BASE = (
        auto(),
        NAUTILAI__ADMIN,
        None,
        [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    NAUTILAI__RW_ALL_DATA = (
        auto(),
        NAUTILAI__ADMIN,
        NAUTILAI__BASE,
        [ScopeTags.NAUTILAI, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE],
    )
    ADVANCED_ANALYSIS__ADMIN = (
        auto(),
        CURI__ADMIN,
        None,
        [ScopeTags.ADVANCED_ANALYSIS, ScopeTags.ADVANCED_ANALYSIS_READ, ScopeTags.ADMIN],
    )
    ADVANCED_ANALYSIS__BASE = (
        auto(),
        ADVANCED_ANALYSIS__ADMIN,
        None,
        [ScopeTags.ADVANCED_ANALYSIS, ScopeTags.ADVANCED_ANALYSIS_READ, ScopeTags.ADVANCED_ANALYSIS_WRITE],
    )
    REFRESH = auto(), None, None, [ScopeTags.UNASSIGNABLE]
    USER__VERIFY = auto(), None, None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    USER__RESET = auto(), None, None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    ADMIN__VERIFY = auto(), None, None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]
    ADMIN__RESET = auto(), None, None, [ScopeTags.ACCOUNT, ScopeTags.UNASSIGNABLE]

    def is_admin_scope(self) -> bool:
        return ScopeTags.ADMIN in self.tags

    def is_user_scope(self) -> bool:
        return ScopeTags.ADMIN not in self.tags


class ScopeConverter(BaseModel):
    @field_validator("scopes", check_fields=False)
    def convert_scopes(cls, scopes):
        if scopes is None:
            return None

        return [convert_scope_str(s) for s in scopes]


def convert_scope_str(scope_str: str) -> Scopes:
    return Scopes[scope_str.upper().replace(":", "__")]


_PRODUCT_SCOPE_TAGS = frozenset({ScopeTags.MANTARRAY, ScopeTags.NAUTILAI, ScopeTags.ADVANCED_ANALYSIS})


def get_product_tags_of_admin(admin_scopes: list[Scopes]) -> set[ScopeTags]:
    return {tag for s in admin_scopes for tag in s.tags if s.is_admin_scope()} & _PRODUCT_SCOPE_TAGS


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

    assignable_scopes = []
    for s in Scopes:
        if s.is_admin_scope():
            continue
        if (s.required_admin is None or s.required_admin in admin_scopes) and not (
            unassignable_tags & s.tags
        ):
            assignable_scopes.append(s)

    return assignable_scopes


def get_assignable_admin_scopes(admin_scopes: list[Scopes]) -> list[Scopes]:
    if Scopes.CURI__ADMIN not in admin_scopes:
        return []

    return [
        s
        for s in Scopes
        if s.is_admin_scope() and ScopeTags.INTERNAL not in s.tags and ScopeTags.UNASSIGNABLE not in s.tags
    ]


def get_scope_dependencies(scopes: list[Scopes]) -> dict[Scopes, Scopes | None]:
    return {s: s.prerequisite for s in scopes}


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
