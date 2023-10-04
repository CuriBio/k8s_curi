from immutabledict import immutabledict

CURIBIO_SCOPE = frozenset(["curi:admin"])

CUSTOMER_SCOPES = frozenset(["nautilus:free", "nautilus:paid", "mantarray:free", "mantarray:paid"])
ACCOUNT_SCOPES = frozenset(["users:verify", "users:reset", "customer:reset"])
NAUTILUS_SCOPES = frozenset(["nautilus:free", "nautilus:paid", "nautilus:rw_all_data"])
# not currently auto assigned anywhere
DEFAULT_MANTARRAY_SCOPES = frozenset(
    ["mantarray:serial_number:edit", "mantarray:firmware:edit", "mantarray:firmware:get"]
)

MANTARRAY_SCOPES = frozenset(["mantarray:free", "mantarray:paid", "mantarray:rw_all_data"])

# ignore free or paid tier scopes, will only send product name to FE to select for user, only contain special scopes
USER_SCOPES = immutabledict({"nautilus": ["nautilus:rw_all_data"], "mantarray": ["mantarray:rw_all_data"]})

PULSE3D_USER_SCOPES = frozenset([*MANTARRAY_SCOPES, *NAUTILUS_SCOPES])
ALL_PULSE3D_SCOPES = frozenset([*CUSTOMER_SCOPES, *MANTARRAY_SCOPES, *NAUTILUS_SCOPES])

PULSE3D_PAID_USAGE = immutabledict(
    {
        "mantarray": {"uploads": -1, "jobs": -1, "expiration_date": None},
        "nautilus": {"uploads": -1, "jobs": -1, "expiration_date": None},
    }
)
