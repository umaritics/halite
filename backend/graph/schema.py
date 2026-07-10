NODE_LABELS = ("Component", "Decision", "Commit", "Ticket", "Document")

RELATIONSHIP_TYPES = (
    "ABOUT",
    "DEPENDS_ON",
    "EXTRACTED_FROM",
    "REFERENCED_IN",
    "MODIFIED",
    "MAY_INVALIDATE",
    "SUPERSEDES",
    "RELATES_TO",
)

SCHEMA_INDEXES = [
    "CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)",
    "CREATE INDEX component_file IF NOT EXISTS FOR (c:Component) ON (c.file_path)",
    "CREATE INDEX decision_status IF NOT EXISTS FOR (d:Decision) ON (d.status)",
    "CREATE INDEX commit_sha IF NOT EXISTS FOR (c:Commit) ON (c.id)",
    "CREATE INDEX ticket_id IF NOT EXISTS FOR (t:Ticket) ON (t.id)",
]
