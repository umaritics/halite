import logging
import time
import uuid

import httpx

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

CODE_EXTENSIONS = {".py", ".ts", ".js", ".java", ".go", ".cs"}


class CodeAgent(BaseAgent):
    def run(self, payload: dict) -> dict:
        owner = payload["owner"]
        repo = payload["repo"]
        if not self._gitea_configured():
            return self._demo_analyze(owner, repo)

        files_processed = 0
        try:
            with httpx.Client(timeout=30) as client:
                tree_resp = client.get(
                    f"{self._base_url}/api/v1/repos/{owner}/{repo}/git/trees/main",
                    headers=self._headers(),
                    params={"recursive": "true"},
                )
                if tree_resp.status_code != 200:
                    tree_resp = client.get(
                        f"{self._base_url}/api/v1/repos/{owner}/{repo}/git/trees/master",
                        headers=self._headers(),
                        params={"recursive": "true"},
                    )
                tree_resp.raise_for_status()
                entries = [
                    e for e in tree_resp.json().get("tree", [])
                    if any(e.get("path", "").endswith(ext) for ext in CODE_EXTENSIONS)
                ][:50]

                for entry in entries:
                    path = entry["path"]
                    raw_resp = client.get(
                        f"{self._base_url}/api/v1/repos/{owner}/{repo}/raw/{path}",
                        headers=self._headers(),
                    )
                    if raw_resp.status_code != 200:
                        continue
                    content = raw_resp.text
                    if content.count("\n") > 500:
                        continue
                    self._analyze_file(path, content)
                    files_processed += 1
                    time.sleep(0.5)
        except Exception as exc:
            logger.error("CodeAgent error: %s", exc)
            return self._demo_analyze(owner, repo)

        return {"files_processed": files_processed, "components_created": files_processed}

    def _analyze_file(self, path: str, content: str):
        prompt = f"""Analyze this code file and return JSON:
{{
  "component_name": "short name",
  "component_type": "module|service|class|feature|api_endpoint",
  "description": "1-2 sentence summary",
  "dependencies": ["list of module names"]
}}
Return ONLY valid JSON.

File: {path}
```
{content[:4000]}
```"""
        raw = self.groq_service.extract_json(prompt)
        parsed = self.graph_repo.parse_json_safe(raw)
        if not isinstance(parsed, dict):
            return

        component = self.graph_repo.create_component(
            {
                "id": str(uuid.uuid4()),
                "name": parsed.get("component_name", path.split("/")[-1]),
                "type": parsed.get("component_type", "module"),
                "file_path": path,
                "description": parsed.get("description", ""),
                "language": path.rsplit(".", 1)[-1],
            }
        )
        for dep_name in parsed.get("dependencies", []):
            dep = self.graph_repo.find_or_create_component_by_name(dep_name)
            if hasattr(self.graph_repo.store, "link_component_depends"):
                self.graph_repo.store.link_component_depends(component["id"], dep["id"])

    def _demo_analyze(self, owner: str, repo: str) -> dict:
        components = [
            ("src/auth/auth.service.ts", "AuthModule", "JWT authentication service"),
            ("src/api/gateway.ts", "ApiGateway", "API routing gateway"),
            ("src/db/postgres.ts", "DatabaseLayer", "PostgreSQL data access"),
        ]
        for path, name, desc in components:
            self.graph_repo.create_component(
                {
                    "name": name,
                    "type": "module",
                    "file_path": path,
                    "description": desc,
                    "language": "typescript",
                }
            )
        return {"files_processed": len(components), "components_created": len(components), "demo": True}

    def _gitea_configured(self) -> bool:
        return bool(getattr(self, "gitea_base_url", None) and getattr(self, "gitea_token", None))

    def _base_url(self) -> str:
        return getattr(self, "gitea_base_url", "").rstrip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"token {getattr(self, 'gitea_token', '')}"}
