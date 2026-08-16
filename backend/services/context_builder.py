import logging
import re

logger = logging.getLogger(__name__)

_INVENTORY_CUES = (
    "list every",
    "list all",
    "every decision",
    "all decisions",
    "which decisions",
    "owned by",
    "named component",
    "depends on",
    "related to",
    "inventory",
)

_FILE_PATH_RE = re.compile(r"\b[\w./-]+\.\w{1,5}\b")
_PASCAL_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]+(?:Module|Layer|Gateway|Service|Alerts?)?\b")
_ENTITY_STOPWORDS = {
    "list",
    "every",
    "decision",
    "decisions",
    "component",
    "components",
    "named",
    "owned",
    "depends",
    "either",
    "which",
    "single",
    "file",
    "path",
    "commit",
    "matching",
    "anchor",
    "invalidation",
    "then",
    "say",
    "what",
    "when",
    "where",
    "based",
    "context",
    "please",
    "tell",
    "about",
}


def build_context_for_query(query: str, graph_repo, groq_service) -> tuple[str, list]:
    components_catalog = graph_repo.list_components()
    entities = _extract_entities(query, components_catalog, graph_repo, groq_service)
    broad = _is_broad_inventory_query(query)

    matched_components, matched_decisions = graph_repo.search_entities(entities)

    # Ensure every catalog component named in the query is included
    by_name = {c.get("name", "").lower(): c for c in components_catalog if c.get("name")}
    for entity in entities:
        key = entity.lower()
        if key in by_name and all(c.get("id") != by_name[key]["id"] for c in matched_components):
            matched_components.append(by_name[key])

    if broad:
        # Inventory questions need the full decision set with component links
        for decision in graph_repo.list_decisions():
            if all(d.get("id") != decision.get("id") for d in matched_decisions):
                matched_decisions.append(decision)
        for comp in components_catalog:
            if not _is_substantive_component(comp, entities):
                continue
            if all(c.get("id") != comp.get("id") for c in matched_components):
                matched_components.append(comp)

    # Drop noisy LLM-invented components (e.g. "billing", "mobile app") unless named in the query
    matched_components = [c for c in matched_components if _is_substantive_component(c, entities)]

    sources: list[dict] = []
    context_parts: list[str] = []
    seen_decision_ids: set[str] = set()
    seen_component_ids: set[str] = set()

    for comp in matched_components:
        cid = comp.get("id")
        if not cid or cid in seen_component_ids:
            continue
        seen_component_ids.add(cid)
        _append_component(comp, sources, context_parts)

        neighborhood = graph_repo.get_neighborhood(cid) or {}
        for n in neighborhood.get("neighbors", []):
            node = n.get("node") or {}
            rel = n.get("relationship") or ""
            label = node.get("label") or ""

            if label == "Decision" or (node.get("title") and not node.get("name")):
                _append_decision(
                    node,
                    sources,
                    context_parts,
                    seen_decision_ids,
                    prefix="  Linked Decision",
                    extra=f" (via {rel})" if rel else "",
                )
            elif label == "Component" or (node.get("name") and not node.get("title")):
                if node.get("id") and node["id"] not in seen_component_ids:
                    if not _is_substantive_component(node, entities):
                        continue
                    seen_component_ids.add(node["id"])
                    dep = f"Depends on" if rel == "DEPENDS_ON" else f"Related component ({rel})"
                    context_parts.append(
                        f"  {dep}: {node.get('name')} — path: {node.get('file_path') or 'N/A'}"
                    )
                    sources.append(
                        {"type": "Component", "id": node["id"], "title": node.get("name", "")}
                    )
            elif label == "Ticket" or (node.get("title") and node.get("type") in ("issue", "pr", None) and "body" in node):
                context_parts.append(
                    f"  Ticket #{node.get('id', '?')}: {node.get('title', '')} "
                    f"[{node.get('status', 'open')}] — {str(node.get('body', ''))[:200]}"
                )
                sources.append(
                    {
                        "type": "Ticket",
                        "id": str(node.get("id", "")),
                        "title": node.get("title", ""),
                    }
                )

        # Explicit ABOUT edges via get_decision enrichment when available
        for decision in matched_decisions:
            names = decision.get("component_names") or []
            if comp.get("name") in names and decision.get("id") not in seen_decision_ids:
                _append_decision(decision, sources, context_parts, seen_decision_ids)

    for decision in matched_decisions:
        if decision.get("id") in seen_decision_ids:
            continue
        full = graph_repo.get_decision(decision["id"]) or decision
        _append_decision(full, sources, context_parts, seen_decision_ids)
        for linked in full.get("components") or []:
            if linked.get("id") and linked["id"] not in seen_component_ids:
                if not _is_substantive_component(linked, entities):
                    continue
                seen_component_ids.add(linked["id"])
                _append_component(linked, sources, context_parts, indent="  ")

    # Always surface commit-matching file paths when invalidation / file / commit is relevant
    if broad or any(k in query.lower() for k in ("invalidat", "commit", "file path", "anchor", "gitea")):
        paths = [
            f"- {c.get('name')}: {c.get('file_path')}"
            for c in components_catalog
            if c.get("file_path")
        ]
        if paths:
            context_parts.append(
                "Commit-matching component file paths (invalidation anchors):\n" + "\n".join(paths)
            )

    if broad:
        inventory = _build_inventory_map(matched_decisions, entities, components_catalog)
        if inventory:
            context_parts.insert(0, inventory)

    context_parts = _dedupe_decision_blocks(context_parts)
    context = "\n\n".join(context_parts[:40])
    unique_sources = _unique_sources(sources)
    return context[:8000], unique_sources[:25]


def _extract_entities(query: str, components_catalog: list[dict], graph_repo, groq_service) -> list[str]:
    entities: list[str] = []

    q_lower = query.lower()
    for comp in components_catalog:
        name = (comp.get("name") or "").strip()
        path = (comp.get("file_path") or "").strip()
        if name and name.lower() in q_lower:
            entities.append(name)
        if path and path.lower() in q_lower:
            entities.append(name or path)

    entities.extend(
        t for t in _PASCAL_RE.findall(query) if t.lower() not in _ENTITY_STOPWORDS
    )
    entities.extend(_FILE_PATH_RE.findall(query))

    # Topic keywords that often appear in decision titles/reasoning
    for kw in (
        "JWT",
        "session",
        "PostgreSQL",
        "MongoDB",
        "ApiGateway",
        "event-driven",
        "invalidation",
        "Alerts",
        "refresh token",
        "AuthModule",
        "DatabaseLayer",
    ):
        if kw.lower() in q_lower:
            entities.append(kw)

    try:
        entity_prompt = f"""Extract software component names, module names, file paths, and decision topics from this query.
Prefer exact names like AuthModule, DatabaseLayer, ApiGateway, Alerts, JWT, PostgreSQL.
Return ONLY JSON: {{"entities": ["name1", "name2"]}}
Query: {query}"""
        raw = groq_service.extract_json(entity_prompt)
        parsed = graph_repo.parse_json_safe(raw)
        if isinstance(parsed, dict):
            entities.extend(parsed.get("entities") or [])
    except Exception as exc:
        logger.warning("Entity extraction LLM failed: %s", exc)

    if not entities:
        entities = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", query) if len(w) > 3][:8]

    # Dedupe preserving order
    seen = set()
    unique = []
    for e in entities:
        key = e.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(e.strip())
    return unique[:20]


def _is_broad_inventory_query(query: str) -> bool:
    q = query.lower()
    return any(cue in q for cue in _INVENTORY_CUES)


def _is_substantive_component(comp: dict, entities: list[str]) -> bool:
    """Prefer real modules/services over incidental nouns from extraction."""
    name = (comp.get("name") or "").strip()
    if not name:
        return False
    entity_keys = {e.lower() for e in entities}
    canonical = {"authmodule", "apigateway", "databaselayer", "alerts"}
    if name.lower() in entity_keys or name.lower() in canonical:
        return True
    if comp.get("file_path"):
        return True
    # Multi-word lowercase phrases are usually noise ("mobile app", "user accounts")
    if " " in name and not name[:1].isupper():
        return False
    if name.islower():
        return False
    # Bare PascalCase without a file path is often an extracted noun (Gitea, UI)
    return False


def _build_inventory_map(
    decisions: list[dict], entities: list[str], components_catalog: list[dict]
) -> str:
    """Compact component → decisions map so the LLM does not drop items."""
    focus = ["AuthModule", "DatabaseLayer", "ApiGateway", "Alerts"]
    for e in entities:
        if e.lower() in _ENTITY_STOPWORDS:
            continue
        if e in focus or _PASCAL_RE.fullmatch(e):
            if e not in focus:
                focus.append(e)

    topic_hints = {
        "AuthModule": ("jwt", "session", "refresh", "authmodule", "token"),
        "DatabaseLayer": ("postgres", "mongodb", "mongo", "database", "acid"),
        "ApiGateway": ("gateway", "routing", "rate limit", "apigateway"),
        "Alerts": ("invalidat", "event-driven", "alert", "gitea sync"),
    }

    buckets: dict[str, list[str]] = {name: [] for name in focus}
    seen_titles: set[str] = set()

    for decision in decisions:
        title = (decision.get("title") or "").strip()
        if not title:
            continue
        key = " ".join(sorted(_token_set(title)))
        if key in seen_titles:
            continue
        seen_titles.add(key)

        names = {
            n
            for n in (
                decision.get("component_names")
                or [c.get("name") for c in (decision.get("components") or []) if c.get("name")]
            )
            if n
        }
        blob = f"{title} {decision.get('reasoning', '')}".lower()
        for name in focus:
            linked = name in names
            hinted = any(h in blob for h in topic_hints.get(name, ()))
            if linked or hinted:
                if title not in buckets[name]:
                    buckets[name].append(title)

    lines = [
        "Inventory map (use this as the checklist for list/every questions):",
    ]
    for name, titles in buckets.items():
        if titles:
            lines.append(f"- {name}: " + "; ".join(titles))
        else:
            lines.append(f"- {name}: (no linked decisions found)")

    auth = next((c for c in components_catalog if c.get("name") == "AuthModule"), None)
    if auth and auth.get("file_path"):
        lines.append(f"Primary invalidation file path for AuthModule: {auth['file_path']}")
    return "\n".join(lines)


def _append_component(comp: dict, sources: list, context_parts: list, indent: str = "") -> None:
    sources.append({"type": "Component", "id": comp["id"], "title": comp.get("name", "")})
    context_parts.append(
        f"{indent}Component: {comp.get('name')} ({comp.get('type', 'module')})\n"
        f"{indent}Path: {comp.get('file_path') or 'N/A'}\n"
        f"{indent}Description: {comp.get('description', '')}"
    )


def _append_decision(
    decision: dict,
    sources: list,
    context_parts: list,
    seen_ids: set[str],
    prefix: str = "Decision",
    extra: str = "",
) -> None:
    did = decision.get("id")
    if not did or did in seen_ids:
        return
    if not decision.get("title"):
        return
    seen_ids.add(did)
    status = decision.get("status", "active")
    components = decision.get("components") or []
    raw_names = decision.get("component_names") or [c.get("name") for c in components if c.get("name")]
    path_backed = {
        (c.get("name") or "")
        for c in components
        if c.get("file_path") or _PASCAL_RE.fullmatch(c.get("name") or "")
    }
    names = [n for n in raw_names if n and (n in path_backed or _PASCAL_RE.fullmatch(str(n)))]
    owned = f"\nOwned/related components: {', '.join(names)}" if names else ""
    tickets = decision.get("tickets") or []
    ticket_bits = ""
    if tickets:
        ticket_bits = "\nTickets: " + "; ".join(
            f"#{t.get('id')} {t.get('title')} [{t.get('status', 'open')}]" for t in tickets
        )
    context_parts.append(
        f"{prefix} [{status}]: {decision.get('title')}{extra}\n"
        f"Reasoning: {decision.get('reasoning', '')}{owned}{ticket_bits}\n"
        f"Source: {decision.get('source', 'unknown')} ({decision.get('source_ref', '')})"
    )
    sources.append(
        {
            "type": "Decision",
            "id": did,
            "title": decision.get("title", ""),
            "status": status,
        }
    )


def _token_set(text: str) -> set[str]:
    stop = {"use", "the", "a", "an", "over", "and", "for", "with", "to", "of", "in", "on"}
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in stop and len(t) > 1}


def _dedupe_decision_blocks(parts: list[str]) -> list[str]:
    """Drop near-duplicate Decision blocks (seed + re-ingest), keep richer text."""
    kept: list[str] = []
    decision_sigs: list[tuple[set[str], int]] = []

    for part in parts:
        if not part.startswith("Decision [") and not part.startswith("  Linked Decision"):
            kept.append(part)
            continue
        # title line is first line
        title_line = part.split("\n", 1)[0]
        tokens = _token_set(title_line)
        duplicate_at = None
        for i, (prev_tokens, _) in enumerate(decision_sigs):
            union = prev_tokens | tokens
            if not union:
                continue
            if len(prev_tokens & tokens) / len(union) >= 0.55:
                duplicate_at = i
                break
        if duplicate_at is None:
            decision_sigs.append((tokens, len(kept)))
            kept.append(part)
            continue
        # Prefer longer / more detailed block
        prev_idx = decision_sigs[duplicate_at][1]
        if len(part) > len(kept[prev_idx]):
            kept[prev_idx] = part
            decision_sigs[duplicate_at] = (tokens, prev_idx)
    return kept


def _unique_sources(sources: list[dict]) -> list[dict]:
    unique = []
    seen = set()
    for s in sources:
        key = (s.get("type"), s.get("id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique
