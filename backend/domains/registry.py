"""
domains/registry.py — Central domain registry.

Usage
-----
    from domains.registry import get_adapter, list_domains, DEFAULT_DOMAIN

    adapters = list_domains()             # [{"key": "software", ...}, ...]
    adapter = get_adapter("maintenance")  # MaintenanceDomainAdapter instance
"""
import logging

from domains.base import DomainAdapter
from domains.maintenance import MaintenanceDomainAdapter
from domains.software import SoftwareDomainAdapter

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Registry — add new adapters here; the rest of the system
# discovers them automatically via list_domains() / get_adapter().
# ------------------------------------------------------------------
_REGISTRY: dict[str, DomainAdapter] = {
    "software": SoftwareDomainAdapter(),
    "maintenance": MaintenanceDomainAdapter(),
}

DEFAULT_DOMAIN: str = "software"


def get_adapter(key: str) -> DomainAdapter:
    """
    Return the adapter for the given domain key.

    Raises KeyError if the key is not registered (explicit failure — no
    silent fallback to software domain).
    """
    if key not in _REGISTRY:
        raise KeyError(
            f"Domain {key!r} is not registered. "
            f"Available domains: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[key]


def list_domains() -> list[dict]:
    """
    Return a list of domain descriptors suitable for the /api/domains endpoint.

    Each dict contains:
      key           — the registry key used in API requests
      display_name  — human-readable label for the UI switcher
      subject_label — graph node label for the primary subject
      record_label  — graph node label for the primary record
      is_default    — True for DEFAULT_DOMAIN
    """
    return [
        {
            "key": adapter.key,
            "display_name": adapter.display_name,
            "subject_label": adapter.subject_label,
            "record_label": adapter.record_label,
            "is_default": adapter.key == DEFAULT_DOMAIN,
        }
        for adapter in _REGISTRY.values()
    ]
