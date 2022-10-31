CUSTOMER_SCOPES = frozenset(["customer:free", "customer:paid"])
PULSE3D_USER_SCOPES = frozenset(["pulse3d:free", "pulse3d:paid"])
PULSE3D_SCOPES = frozenset([*CUSTOMER_SCOPES, *PULSE3D_USER_SCOPES])
