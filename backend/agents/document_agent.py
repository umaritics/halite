import io
import logging
import uuid

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DocumentAgent(BaseAgent):
    SYSTEM_PROMPT = """You are extracting software decisions from a document.
For each decision found, return JSON with: decisions (list of objects with title, reasoning, related_components).
If no decisions are found, return {"decisions": []}.
Return ONLY valid JSON, no explanation."""

    def run(self, payload: dict) -> dict:
        filename = payload["filename"]
        content = payload["content"]
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        text = self._parse_content(content, file_type, filename)
        chunks = self._chunk_text(text)
        decisions_created = 0

        document = self.graph_repo.create_document(
            {
                "filename": filename,
                "file_type": file_type,
                "processed": True,
                "summary": text[:500],
            }
        )

        for chunk in chunks:
            prompt = f"{self.SYSTEM_PROMPT}\n\nDocument chunk:\n{chunk}"
            raw = self.groq_service.extract_json(prompt)
            parsed = self.graph_repo.parse_json_safe(raw)
            items = parsed.get("decisions", []) if isinstance(parsed, dict) else []

            for item in items:
                decision = self.graph_repo.create_decision(
                    {
                        "id": str(uuid.uuid4()),
                        "title": item.get("title", "Untitled decision"),
                        "reasoning": item.get("reasoning", ""),
                        "status": "active",
                        "source": "document",
                        "source_ref": filename,
                        "created_by": "document_agent",
                    }
                )
                self.graph_repo.link_decision_document(decision["id"], document["id"])
                for comp_name in item.get("related_components", []):
                    component = self.graph_repo.find_or_create_component_by_name(comp_name)
                    self.graph_repo.link_decision_about(decision["id"], component["id"])
                decisions_created += 1

        return {"decisions_created": decisions_created, "document_id": document["id"]}

    def _parse_content(self, content: bytes, file_type: str, filename: str) -> str:
        try:
            if file_type == "pdf":
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(content))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            if file_type == "docx":
                import docx2txt

                return docx2txt.process(io.BytesIO(content))
            return content.decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.error("Document parse error for %s: %s", filename, exc)
            return content.decode("utf-8", errors="ignore")

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + chunk_size])
            start += chunk_size - overlap
        return chunks[:10]
