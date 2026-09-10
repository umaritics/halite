"""
domains/software.py — Software-engineering domain adapter.

Wraps the existing software domain behaviour with ZERO change to existing
call sites.  This adapter exists purely so that both domains are visibly
siblings, and so the domain switcher has a concrete object to describe the
software side.

Source authority hierarchy (lower number = lower authority):
  1  meeting_transcript  — informal, no reviewer gate
  2  document            — uploaded document, reviewed by uploader
  3  direct_commit       — code already merged
  4  gitea_pr            — reviewed pull-request
"""
import logging

from domains.base import DomainAdapter

logger = logging.getLogger(__name__)

_SOURCE_AUTHORITY: dict[str, int] = {
    "manual": 1,
    "meeting_transcript": 1,
    "document": 2,
    "direct_commit": 3,
    "gitea_pr": 4,
}


class SoftwareDomainAdapter(DomainAdapter):
    key = "software"
    display_name = "Software Engineering"
    subject_label = "Component"
    record_label = "Decision"

    def subject_key(self, raw_record: dict) -> str | None:
        """
        For a Decision record the subject is the component name.

        raw_record is a Decision dict that may carry 'component_names' (list)
        or a single 'component' key.  Return the first non-empty name, or None.
        """
        # List form from list_decisions
        names = raw_record.get("component_names") or []
        if names:
            return names[0] or None
        # Single component dict (from get_decision)
        comp = raw_record.get("component")
        if isinstance(comp, dict):
            return comp.get("name") or None
        return None

    def timestamp(self, raw_record: dict) -> str | None:
        """Return created_at for a Decision — already ISO-8601."""
        ts = raw_record.get("created_at") or raw_record.get("updated_at")
        return ts or None

    def source_authority(self, raw_record: dict) -> int:
        source = raw_record.get("source", "manual").lower()
        return _SOURCE_AUTHORITY.get(source, 1)

    def record_text(self, raw_record: dict) -> str:
        title = raw_record.get("title", "")
        reasoning = raw_record.get("reasoning", "")
        return f"{title}. {reasoning}".strip(". ") if (title or reasoning) else ""
