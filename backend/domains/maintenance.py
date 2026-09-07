"""
domains/maintenance.py — Aviation maintenance / FAA SDR domain adapter.

Source authority:
  5  faa_sdr — regulatory filing, highest possible authority.
               FAA SDRs are legally required submissions; they cannot be
               informally overridden.

subject_key returns the tail number (RegistryNNumber), which is the
physical asset identity used throughout the maintenance domain.

timestamp parses DifficultyDate (MM/DD/YYYY).  If it cannot be parsed
it returns None — the agent skips the record rather than defaulting to today.
"""
import logging
import re
from datetime import datetime

from domains.base import DomainAdapter

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%m/%d/%Y"


class MaintenanceDomainAdapter(DomainAdapter):
    key = "maintenance"
    display_name = "Maintenance / Field Service"
    subject_label = "Asset"
    record_label = "ServiceRecord"

    def subject_key(self, raw_record: dict) -> str | None:
        """Return tail number (RegistryNNumber).  None if blank."""
        tail = raw_record.get("RegistryNNumber", "").strip()
        return tail if tail else None

    def timestamp(self, raw_record: dict) -> str | None:
        """
        Parse DifficultyDate (MM/DD/YYYY) → ISO-8601 date string.

        Returns None — never raises — if the field is absent or unparseable.
        The caller must count and skip these records, not default them.
        """
        raw = raw_record.get("DifficultyDate", "").strip()
        if not raw:
            return None
        try:
            dt = datetime.strptime(raw, _DATE_FORMAT)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            logger.debug("Unparseable DifficultyDate: %r", raw)
            return None

    def source_authority(self, raw_record: dict) -> int:
        """FAA SDR = 5 (regulatory filing)."""
        return 5

    def record_text(self, raw_record: dict) -> str:
        """Return the Discrepancy field — the primary free text of an SDR."""
        return (raw_record.get("Discrepancy") or "").strip()
