from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agents.decision_agent import DecisionAgent
from api.deps import get_graph_repo, get_groq_service

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


@router.post("/chat")
def chat(req: ChatRequest, graph_repo=Depends(get_graph_repo), groq_service=Depends(get_groq_service)):
    from services.context_builder import build_context_for_query

    context, sources = build_context_for_query(req.message, graph_repo, groq_service)

    system_prompt = f"""You are Halite, an AI assistant that answers questions about a software project.
You have access to the project's knowledge graph which contains decisions, components, and their reasoning.

KNOWLEDGE GRAPH CONTEXT:
{context}

Rules:
- Answer using ALL relevant items in the context — do not stop after the first match
- If an "Inventory map" is present, your answer MUST cover every component line that lists decisions
- For inventory / "list every" questions, enumerate each matching Decision and name its related Component(s)
- When the question asks for a commit-matching or invalidation file path, give the exact Path from the context
- Prefer Component Path fields (e.g. src/auth/auth.service.ts) over guessing
- Attribute ownership only via "Owned/related components" / Component links / Inventory map in the context — do not invent owners
- If two Decision titles look like duplicates of the same choice, merge them into one bullet
- Only say information is missing after you have checked the full context
- Always cite which Decision or Component your answer is based on
- If a Decision has status "needs_review" or "invalidated", warn the user
- Be direct and technical"""

    messages = list(req.conversation_history) + [{"role": "user", "content": req.message}]
    reply = groq_service.chat(messages=messages, system_prompt=system_prompt)
    return {"reply": reply, "sources": sources}
