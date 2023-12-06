from enum import Enum, StrEnum, auto


class ProhibitedScopeError(Exception):
    pass


class ScopeTags(Enum):
    INTERNAL = auto()  # TODO rename this to production?
    MANTARRAY = auto()
    NAUTILUS = auto()
    DEFAULT = auto()
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
    MANTARRAY__BASE = (
        auto(),
        ScopeTags.DEFAULT,
        ScopeTags.MANTARRAY,
        ScopeTags.PULSE3D_READ,
        ScopeTags.PULSE3D_WRITE,
    )
    MANTARRAY__FIRMWARE__GET = auto(), ScopeTags.DEFAULT, ScopeTags.MANTARRAY
    MANTARRAY__SOFTWARE__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__FIRMWARE__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__FIRMWARE__LIST = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__SERIAL_NUMBER__EDIT = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    MANTARRAY__SERIAL_NUMBER__LIST = auto(), ScopeTags.MANTARRAY, ScopeTags.INTERNAL
    NAUTILUS__ADMIN = auto(), ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.ADMIN
    NAUTILUS__RW_ALL_DATA = auto(), ScopeTags.NAUTILUS, ScopeTags.PULSE3D_READ, ScopeTags.PULSE3D_WRITE
    NAUTILUS__BASE = (
        auto(),
        ScopeTags.DEFAULT,
        ScopeTags.NAUTILUS,
        ScopeTags.PULSE3D_READ,
        ScopeTags.PULSE3D_WRITE,
    )
    # TODO need to revisit these
    REFRESH = auto()
    NON_ADMIN__VERIFY = auto(), ScopeTags.ACCOUNT
    NON_ADMIN__RESET = auto(), ScopeTags.ACCOUNT
    ADMIN__VERIFY = auto(), ScopeTags.ACCOUNT
    ADMIN__RESET = auto(), ScopeTags.ACCOUNT


# TODO add testing for these
def get_product_tags_of_admin(admin_scopes) -> set[Scopes]:
    return {tag for s in admin_scopes for tag in s.tags} & {ScopeTags.MANTARRAY, ScopeTags.NAUTILUS}


def check_prohibited_product(admin_scopes, product) -> None:
    product_tags_of_admin = get_product_tags_of_admin(admin_scopes)

    if product not in product_tags_of_admin:
        # TODO make a specific exception for this
        raise Exception(product)


def get_assignable_scopes_from_admin(admin_scopes) -> dict[str, list[str]]:
    unassignable_tags = {ScopeTags.ADMIN}
    if Scopes.CURI__ADMIN not in admin_scopes:
        unassignable_tags += ScopeTags.INTERNAL

    product_tags_of_admin = get_product_tags_of_admin(admin_scopes)

    assignable_scopes = {}
    for ptag in product_tags_of_admin:
        assignable_scopes_for_product = [
            s for s in Scopes if ptag in s.tags and not (unassignable_tags & s.tags)
        ]
        assignable_scopes[ptag.name.lower()] = assignable_scopes_for_product

    return assignable_scopes


def check_prohibited_scopes(user_scopes, admin_scopes) -> None:
    assignable_scopes = get_assignable_scopes_from_admin(admin_scopes)
    if prohibited_scopes := set(user_scopes) - set(assignable_scopes):
        raise ProhibitedScopeError(f"Attempting to assign prohibited scope(s): {prohibited_scopes}")
