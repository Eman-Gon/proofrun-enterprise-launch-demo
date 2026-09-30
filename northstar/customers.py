"""Customer validation shared by the onboarding endpoints."""


def normalize_customer_id(value):
    """Customer IDs are opaque external references; preserve their spelling."""
    if not isinstance(value, str) or not value:
        raise ValueError("invalid_customer")
    return value


def import_customer(payload):
    """Validate an import request and return its public customer record."""
    if not isinstance(payload, dict):
        raise ValueError("invalid_customer")
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("invalid_customer")
    return {
        "customer_id": normalize_customer_id(payload.get("customer_id")),
        "name": name,
    }
