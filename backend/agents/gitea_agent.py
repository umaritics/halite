import logging
import uuid

import httpx

from agents.base_agent import BaseAgent
from graph.invalidation import check_invalidation

logger = logging.getLogger(__name__)


class GiteaAgent(BaseAgent):
    def __init__(self, graph_repo, groq_service, gitea_base_url: str, gitea_token: str):
        super().__init__(graph_repo, groq_service)
        self.base_url = gitea_base_url.rstrip("/")
        self.token = gitea_token
        self.headers = {"Authorization": f"token {gitea_token}"}

    def run(self, payload: dict) -> dict:
        owner = payload["owner"]
        repo = payload["repo"]
        commits_synced = self._sync_commits(owner, repo)
        tickets_synced = self._sync_tickets(owner, repo)
        return {"commits_synced": commits_synced, "tickets_synced": tickets_synced}

    def process_webhook(self, event_type: str, payload: dict) -> dict:
        if event_type == "push":
            repo = payload.get("repository", {}).get("full_name", "").split("/")
            if len(repo) != 2:
                return {"processed": False}
            results = []
            for commit in payload.get("commits", []):
                sha = commit.get("id", "")[:40]
                files = [f for f in commit.get("added", []) + commit.get("modified", []) + commit.get("removed", [])]
                message = commit.get("message", "")
                author = commit.get("author", {}).get("name", "unknown")
                self.graph_repo.create_commit(
                    {
                        "id": sha,
                        "message": message,
                        "author": author,
                        "timestamp": commit.get("timestamp", ""),
                        "files_changed": files,
                    }
                )
                self._link_commit_files(sha, files)
                flagged = check_invalidation(sha, files, self.graph_repo)
                created = self._extract_decision_from_commit(sha, message, files, author)
                results.append({"sha": sha, "flagged": flagged, "decision_created": created})
            return {"processed": True, "commits": results}
        return {"processed": False, "reason": "unsupported event"}

    def _sync_commits(self, owner: str, repo: str) -> int:
        if not self.base_url or not self.token:
            return self._demo_sync_commits(owner, repo)
        count = 0
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    f"{self.base_url}/api/v1/repos/{owner}/{repo}/commits",
                    headers=self.headers,
                    params={"limit": 20},
                )
                resp.raise_for_status()
                for commit in resp.json():
                    sha = commit["sha"]
                    detail = client.get(
                        f"{self.base_url}/api/v1/repos/{owner}/{repo}/git/commits/{sha}",
                        headers=self.headers,
                    )
                    files = []
                    if detail.status_code == 200:
                        files = [f.get("filename", "") for f in detail.json().get("files", [])]
                    message = commit.get("commit", {}).get("message", "")
                    author = commit.get("commit", {}).get("author", {}).get("name", "")
                    self.graph_repo.create_commit(
                        {
                            "id": sha,
                            "message": message,
                            "author": author,
                            "timestamp": commit.get("commit", {}).get("author", {}).get("date", ""),
                            "files_changed": files,
                        }
                    )
                    self._link_commit_files(sha, files)
                    check_invalidation(sha, files, self.graph_repo)
                    self._extract_decision_from_commit(sha, message, files, author)
                    count += 1
        except Exception as exc:
            logger.error("Gitea sync error: %s", exc)
            return self._demo_sync_commits(owner, repo)
        return count

    def _link_commit_files(self, sha: str, files: list[str]) -> None:
        for fp in files:
            if not fp:
                continue
            comp = self.graph_repo.find_component_by_path(fp)
            if not comp:
                name = fp.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                comp = self.graph_repo.create_component(
                    {
                        "name": name,
                        "type": "module",
                        "file_path": fp,
                        "description": f"Inferred from commit touching {fp}",
                        "language": fp.rsplit(".", 1)[-1] if "." in fp else "unknown",
                    }
                )
            self.graph_repo.link_commit_modified(sha, comp["id"])

    def _extract_decision_from_commit(
        self, sha: str, message: str, files: list[str], author: str
    ) -> dict | None:
        """Create a Decision when the commit records an architectural choice."""
        if not message or not self.groq_service:
            return None
        prompt = f"""You extract software architecture decisions from git commits.
If this commit records a real design choice (e.g. JWT vs sessions, Postgres vs Mongo, gateway, event-driven),
return JSON: {{"decision": {{"title": "...", "reasoning": "...", "related_components": ["AuthModule"]}}}}
If it is a routine code tweak with no new architecture choice, return {{"decision": null}}
Return ONLY JSON.

Commit message:
{message[:1500]}

Changed files:
{', '.join(files[:20])}
"""
        try:
            raw = self.groq_service.extract_json(prompt)
            parsed = self.graph_repo.parse_json_safe(raw)
        except Exception as exc:
            logger.warning("Commit decision extract failed: %s", exc)
            return None
        item = parsed.get("decision") if isinstance(parsed, dict) else None
        if not item or not item.get("title"):
            return None
        decision = self.graph_repo.create_decision(
            {
                "id": str(uuid.uuid4()),
                "title": item.get("title"),
                "reasoning": item.get("reasoning") or message[:500],
                "status": "active",
                "source": "commit",
                "source_ref": sha,
                "created_by": author or "gitea",
            }
        )
        names = list(item.get("related_components") or [])
        for fp in files:
            comp = self.graph_repo.find_component_by_path(fp)
            if comp:
                self.graph_repo.link_decision_about(decision["id"], comp["id"])
                if comp.get("name") and comp["name"] not in names:
                    names.append(comp["name"])
        for name in names:
            component = self.graph_repo.find_or_create_component_by_name(name)
            self.graph_repo.link_decision_about(decision["id"], component["id"])
        logger.info("Created decision from commit %s: %s", sha[:8], decision.get("title"))
        return {"id": decision["id"], "title": decision.get("title")}

    def _demo_sync_commits(self, owner: str, repo: str) -> int:
        sha = "demo" + owner[:4] + repo[:4]
        files = ["src/auth/auth.service.ts"]
        self.graph_repo.create_commit(
            {
                "id": sha,
                "message": f"Demo sync commit for {owner}/{repo}",
                "author": "halite-demo",
                "timestamp": "2026-01-01T00:00:00Z",
                "files_changed": files,
            }
        )
        self._link_commit_files(sha, files)
        check_invalidation(sha, files, self.graph_repo)
        return 1

    def _sync_tickets(self, owner: str, repo: str) -> int:
        if not self.base_url or not self.token:
            return 0
        count = 0
        try:
            with httpx.Client(timeout=30) as client:
                for endpoint, ticket_type in [("issues", "issue"), ("pulls", "pull_request")]:
                    resp = client.get(
                        f"{self.base_url}/api/v1/repos/{owner}/{repo}/{endpoint}",
                        headers=self.headers,
                        params={"state": "all", "limit": 20},
                    )
                    if resp.status_code != 200:
                        continue
                    for item in resp.json():
                        ticket = self.graph_repo.create_ticket(
                            {
                                "id": str(item["number"]),
                                "title": item.get("title", ""),
                                "body": item.get("body", "") or "",
                                "type": ticket_type,
                                "status": item.get("state", "open"),
                                "created_by": item.get("user", {}).get("login", ""),
                            }
                        )
                        if self.groq_service and item.get("body"):
                            raw = self.groq_service.extract_json(
                                f'Extract component names from this ticket. Return JSON: {{"components": ["name"]}}\n{item["body"][:500]}'
                            )
                            parsed = self.graph_repo.parse_json_safe(raw)
                            for name in parsed.get("components", []) if isinstance(parsed, dict) else []:
                                comp = self.graph_repo.find_or_create_component_by_name(name)
                                if hasattr(self.graph_repo, "store"):
                                    self.graph_repo.store.link_ticket_relates(ticket["id"], comp["id"])
                        count += 1
        except Exception as exc:
            logger.error("Gitea ticket sync error: %s", exc)
        return count
