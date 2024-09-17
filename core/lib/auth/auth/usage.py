from immutabledict import immutabledict


DEFAULT_USAGE_LIMITS = immutabledict(
    {
        "mantarray": {"uploads": -1, "jobs": -1, "expiration_date": None},
        "nautilai": {"uploads": -1, "jobs": -1, "expiration_date": None},
        "advanced_analysis": {"jobs": -1, "expiration_date": None},
    }
)
