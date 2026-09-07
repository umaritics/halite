NODE_LABELS = (
    "Component",
    "Decision",
    "Commit",
    "Ticket",
    "Document",
    "Asset",          # maintenance: physical asset, keyed by tail_number
    "ServiceRecord",  # maintenance: a single FAA SDR filing
)

RELATIONSHIP_TYPES = (
    # ── software domain ──────────────────────────────────────────────
    "ABOUT",
    "DEPENDS_ON",
    "EXTRACTED_FROM",
    "REFERENCED_IN",
    "MODIFIED",
    "MAY_INVALIDATE",
    "SUPERSEDES",
    "RELATES_TO",
    # ── maintenance domain ───────────────────────────────────────────
    "PRECEDED_BY",    # ServiceRecord -[PRECEDED_BY]-> earlier ServiceRecord on same asset
    "DERIVED_FROM",   # reserved for future propagation (deferred per §9)
    "FLAGGED_BY",     # Asset or ServiceRecord flagged by an alert
)

SCHEMA_INDEXES = [
    # ── existing ─────────────────────────────────────────────────────
    "CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)",
    "CREATE INDEX component_file IF NOT EXISTS FOR (c:Component) ON (c.file_path)",
    "CREATE INDEX decision_status IF NOT EXISTS FOR (d:Decision) ON (d.status)",
    "CREATE INDEX commit_sha IF NOT EXISTS FOR (c:Commit) ON (c.id)",
    "CREATE INDEX ticket_id IF NOT EXISTS FOR (t:Ticket) ON (t.id)",
    # ── maintenance ───────────────────────────────────────────────────
    "CREATE INDEX asset_tail IF NOT EXISTS FOR (a:Asset) ON (a.tail_number)",
    "CREATE INDEX service_record_id IF NOT EXISTS FOR (sr:ServiceRecord) ON (sr.record_id)",
    "CREATE INDEX service_record_occurred IF NOT EXISTS FOR (sr:ServiceRecord) ON (sr.occurred_at)",
    "CREATE INDEX service_record_status IF NOT EXISTS FOR (sr:ServiceRecord) ON (sr.status)",
]
