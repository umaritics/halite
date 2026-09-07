"""
domains/base.py — Abstract base class for all domain adapters.

A DomainAdapter bridges raw record data to the graph representation.
It is a pure data-transformation object; it does NOT touch the graph directly.
"""
from abc import ABC, abstractmethod


class DomainAdapter(ABC):
    """
    Abstract domain adapter.

    All attributes and methods below MUST be implemented by every adapter.
    The registry enforces this via Python ABC mechanics.
    """

    # ------------------------------------------------------------------
    # Class-level identity — set directly on the concrete class, not in __init__
    # ------------------------------------------------------------------
    key: str          # Registry key, e.g. "software" | "maintenance"
    display_name: str  # Human-readable label shown in the UI switcher
    subject_label: str  # Graph node label for the domain's primary subject
                        #   "Component" (software) | "Asset" (maintenance)
    record_label: str   # Graph node label for the domain's primary record
                        #   "Decision" (software) | "ServiceRecord" (maintenance)

    # ------------------------------------------------------------------
    # Subject identity
    # ------------------------------------------------------------------

    @abstractmethod
    def subject_key(self, raw_record: dict) -> str | None:
        """
        Return the string that uniquely identifies the *subject* of a record.

        Software:    the component name (e.g. "AuthModule")
        Maintenance: the tail number (e.g. "N12345")

        Return None if the record's subject cannot be determined.
        """

    # ------------------------------------------------------------------
    # Temporal ordering
    # ------------------------------------------------------------------

    @abstractmethod
    def timestamp(self, raw_record: dict) -> str | None:
        """
        Return the primary event timestamp for the record as an ISO-8601 string.

        Used for ordering records and computing recency signals.
        Return None if the timestamp is missing or unparseable.
        """

    # ------------------------------------------------------------------
    # Source authority
    # ------------------------------------------------------------------

    @abstractmethod
    def source_authority(self, raw_record: dict) -> int:
        """
        Return a non-negative integer representing how authoritative the record source is.

        Higher = more authoritative. Used by the conflict engine when two records
        from different sources conflict: the one with higher authority wins.

        Software example:  meeting_transcript=1, gitea_pr=3, direct_commit=2
        Maintenance:       faa_sdr=5 (regulatory filing — highest)
        """

    # ------------------------------------------------------------------
    # Free text
    # ------------------------------------------------------------------

    @abstractmethod
    def record_text(self, raw_record: dict) -> str:
        """
        Return the primary free-text body of the record.

        This is the text fed to the LLM for conflict classification.
        Must never return None; return "" if there is no text.
        """
