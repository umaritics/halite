import json
import logging

logger = logging.getLogger(__name__)


def build_context_for_query(query: str, graph_repo, groq_service) -> tuple[str, list]:
    entity_prompt = f"""
    Extract component names, module names, or decision topics from this query.
    Return JSON: {{"entities": ["name1", "name2"]}}
    Query: {query}
    """
    raw = groq_service.extract_json(entity_prompt)
    parsed = graph_repo.parse_json_safe(raw)
    entities = parsed.get("entities", []) if isinstance(parsed, dict) else []

    if not entities:
        entities = [w for w in query.split() if len(w) > 3][:5]

    components, decisions = graph_repo.search_entities(entities)
    sources = []
    context_parts = []

    for comp in components:
        sources.append({"type": "Component", "id": comp["id"], "title": comp.get("name", "")})
        context_parts.append(
            f"Component: {comp.get('name')} ({comp.get('type', 'module')})\n"
            f"Path: {comp.get('file_path', 'N/A')}\n"
            f"Description: {comp.get('description', '')}"
        )
        neighborhood = graph_repo.get_neighborhood(comp["id"])
        for n in neighborhood.get("neighbors", []):
            node = n.get("node", {})
            if node.get("label") == "Decision" or "title" in node:
                if node.get("title"):
                    status = node.get("status", "active")
                    context_parts.append(
                        f"  Linked Decision [{status}]: {node.get('title')} — {node.get('reasoning', '')[:300]}"
                    )
                    sources.append(
                        {
                            "type": "Decision",
                            "id": node["id"],
                            "title": node.get("title", ""),
                            "status": status,
                        }
                    )

    for decision in decisions:
        status = decision.get("status", "active")
        sources.append(
            {
                "type": "Decision",
                "id": decision["id"],
                "title": decision.get("title", ""),
                "status": status,
            }
        )
        context_parts.append(
            f"Decision [{status}]: {decision.get('title')}\n"
            f"Reasoning: {decision.get('reasoning', '')}\n"
            f"Source: {decision.get('source', 'unknown')}"
        )

    if not context_parts:
        all_decisions = graph_repo.list_decisions()[:5]
        for decision in all_decisions:
            status = decision.get("status", "active")
            sources.append(
                {
                    "type": "Decision",
                    "id": decision["id"],
                    "title": decision.get("title", ""),
                    "status": status,
                }
            )
            context_parts.append(
                f"Decision [{status}]: {decision.get('title')}\nReasoning: {decision.get('reasoning', '')}"
            )

    context = "\n\n".join(context_parts[:10])
    unique_sources = []
    seen = set()
    for s in sources:
        key = (s["type"], s["id"])
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)

    return context[:3000], unique_sources[:10]
