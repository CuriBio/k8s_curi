from auth.scopes import (
    Scopes,
    check_prohibited_user_scopes,
    check_prohibited_admin_scopes,
    ProhibitedScopeError,
    MissingScopeDependencyError,
    validate_scope_dependencies,
)
import pytest


def test_all_admin_scope_requirements_are_actually_admin_scopes():
    for s in Scopes:
        if (required_admin := s.required_admin) is not None:
            assert required_admin.is_admin_scope(), s


def test_all_prerequisite_scopes_have_matching_admin_status():
    for s in Scopes:
        if s.prerequisite is None:
            continue
        assert s.prerequisite.is_admin_scope() is s.is_admin_scope(), s


@pytest.mark.parametrize(
    "scopes",
    [
        # admin scopes
        [Scopes.MANTARRAY__ADMIN],
        [Scopes.MANTARRAY__ADMIN, Scopes.MANTARRAY__NMJ],
        [Scopes.MANTARRAY__ADMIN, Scopes.MANTARRAY__CLS_ALG],
        # user scopes
        [Scopes.MANTARRAY__BASE],
        [Scopes.MANTARRAY__BASE, Scopes.MANTARRAY__RW_ALL_DATA],
        [Scopes.MANTARRAY__BASE, Scopes.MANTARRAY__FIRMWARE__LIST, Scopes.MANTARRAY__FIRMWARE__EDIT],
    ],
)
def test_validate_scope_dependencies__valid(scopes):
    # no exception raised means this passed
    validate_scope_dependencies(scopes)


@pytest.mark.parametrize(
    "scopes",
    [
        # admin scopes
        [Scopes.MANTARRAY__NMJ],
        [Scopes.MANTARRAY__CLS_ALG],
        # user scopes
        [Scopes.MANTARRAY__RW_ALL_DATA],
        [Scopes.MANTARRAY__FIRMWARE__LIST, Scopes.MANTARRAY__FIRMWARE__EDIT],
        [Scopes.MANTARRAY__BASE, Scopes.MANTARRAY__FIRMWARE__EDIT],
    ],
)
def test_validate_scope_dependencies__invalid(scopes):
    with pytest.raises(MissingScopeDependencyError):
        validate_scope_dependencies(scopes)


@pytest.mark.parametrize(
    "admin_scopes,user_scope",
    [
        ([Scopes.MANTARRAY__ADMIN], Scopes.MANTARRAY__BASE),
        ([Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__ADMIN], Scopes.MANTARRAY__BASE),
        ([Scopes.MANTARRAY__ADMIN], Scopes.MANTARRAY__RW_ALL_DATA),
        ([Scopes.CURI__ADMIN], Scopes.MANTARRAY__FIRMWARE__LIST),
        ([Scopes.NAUTILAI__ADMIN], Scopes.NAUTILAI__BASE),
    ],
)
def test_check_prohibited_user_scopes__valid(admin_scopes, user_scope):
    # no exception raised means this passed
    check_prohibited_user_scopes([user_scope], admin_scopes)


@pytest.mark.parametrize(
    "admin_scopes,user_scope",
    [
        # user scopes
        ([Scopes.NAUTILAI__ADMIN], Scopes.MANTARRAY__BASE),
        ([Scopes.MANTARRAY__ADMIN], Scopes.MANTARRAY__FIRMWARE__LIST),
        ([Scopes.MANTARRAY__ADMIN], Scopes.NAUTILAI__BASE),
        # other
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.CURI__ADMIN),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.MANTARRAY__ADMIN),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.USER__VERIFY),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.USER__RESET),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.ADMIN__VERIFY),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.ADMIN__RESET),
        ([Scopes.CURI__ADMIN, Scopes.MANTARRAY__ADMIN], Scopes.REFRESH),
    ],
)
def test_check_prohibited_user_scopes__invalid(admin_scopes, user_scope):
    with pytest.raises(ProhibitedScopeError):
        check_prohibited_user_scopes([user_scope], admin_scopes)


@pytest.mark.parametrize(
    "admin_scope",
    [Scopes.MANTARRAY__ADMIN, Scopes.MANTARRAY__NMJ, Scopes.MANTARRAY__CLS_ALG, Scopes.NAUTILAI__ADMIN],
)
def test_check_prohibited_admin_scopes__valid(admin_scope):
    # no exception raised means this passed
    check_prohibited_admin_scopes([admin_scope], [Scopes.CURI__ADMIN])


@pytest.mark.parametrize(
    "other_admin_scope,root_admin_scopes",
    [
        # admin scopes
        (Scopes.CURI__ADMIN, [Scopes.CURI__ADMIN]),
        (Scopes.MANTARRAY__ADMIN, []),
        (Scopes.MANTARRAY__ADMIN, [Scopes.MANTARRAY__ADMIN]),
        # other
        (Scopes.CURI__ADMIN, [Scopes.MANTARRAY__BASE]),
        (Scopes.MANTARRAY__ADMIN, [Scopes.MANTARRAY__BASE]),
        (Scopes.CURI__ADMIN, [Scopes.REFRESH]),
        (Scopes.CURI__ADMIN, [Scopes.USER__VERIFY]),
        (Scopes.CURI__ADMIN, [Scopes.USER__RESET]),
        (Scopes.CURI__ADMIN, [Scopes.ADMIN__VERIFY]),
        (Scopes.CURI__ADMIN, [Scopes.ADMIN__RESET]),
    ],
)
def test_check_prohibited_admin_scopes__invalid(other_admin_scope, root_admin_scopes):
    with pytest.raises(ProhibitedScopeError):
        check_prohibited_user_scopes([other_admin_scope], root_admin_scopes)
