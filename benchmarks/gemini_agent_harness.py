import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


SYSTEM_RULES = """You are benchmarking repository understanding.
Use the available tools to inspect only the minimum necessary project files.
Do not modify code.
When you have enough evidence, call submit_answer.
Prefer narrow verification over broad scanning.
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RepoTools:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.files_read = 0
        self.total_lines_read = 0
        self.search_count = 0
        self.tool_calls = 0

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self.repo_root / relative_path).resolve()
        if self.repo_root.resolve() not in candidate.parents and candidate != self.repo_root.resolve():
            raise ValueError(f"Path escapes repo root: {relative_path}")
        return candidate

    def list_files(self, subpath: str = ".") -> dict:
        self.tool_calls += 1
        root = self._safe_path(subpath)
        items = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                items.append(str(path.relative_to(self.repo_root)).replace("\\", "/"))
        return {"files": items[:200]}

    def read_file(self, relative_path: str, start_line: int = 1, max_lines: int = 200) -> dict:
        self.tool_calls += 1
        path = self._safe_path(relative_path)
        lines = read_text(path).splitlines()
        start = max(start_line - 1, 0)
        end = min(start + max_lines, len(lines))
        window = [f"{idx + 1}:{line}" for idx, line in enumerate(lines[start:end], start=start)]
        self.files_read += 1
        self.total_lines_read += len(window)
        return {"path": relative_path, "start_line": start + 1, "end_line": end, "content": "\n".join(window)}

    def search_files(self, query: str, subpath: str = ".") -> dict:
        self.tool_calls += 1
        self.search_count += 1
        root = self._safe_path(subpath)
        matches = []
        q = query.lower()
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                lines = read_text(path).splitlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if q in line.lower():
                    matches.append(
                        {
                            "path": str(path.relative_to(self.repo_root)).replace("\\", "/"),
                            "line": idx,
                            "snippet": line.strip(),
                        }
                    )
                    if len(matches) >= 50:
                        return {"matches": matches}
        return {"matches": matches}


def gemini_call(api_key: str, model: str, contents: list, tools_schema: list) -> dict:
    url = GEMINI_URL.format(model=urllib.parse.quote(model), key=urllib.parse.quote(api_key))
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RULES}]},
        "contents": contents,
        "tools": [{"functionDeclarations": tools_schema}],
        "generationConfig": {"temperature": 0.2},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def tool_schemas() -> list:
    return [
        {
            "name": "list_files",
            "description": "List repository files under a subpath.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"subpath": {"type": "STRING"}},
            },
        },
        {
            "name": "read_file",
            "description": "Read a file window with line numbers.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "relative_path": {"type": "STRING"},
                    "start_line": {"type": "INTEGER"},
                    "max_lines": {"type": "INTEGER"},
                },
                "required": ["relative_path"],
            },
        },
        {
            "name": "search_files",
            "description": "Search for a text query across repository files.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING"},
                    "subpath": {"type": "STRING"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "submit_answer",
            "description": "Finish the task with your answer and the files you verified.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "answer": {"type": "STRING"},
                    "files_verified": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "confidence": {"type": "STRING"},
                },
                "required": ["answer", "files_verified", "confidence"],
            },
        },
    ]


def run_task(api_key: str, model: str, repo_root: Path, task: dict, context_text: str | None) -> dict:
    repo_tools = RepoTools(repo_root)
    contents = []
    prompt = task["prompt"]
    if context_text:
        prompt = (
            "You are given a Halite project-memory export.\n"
            "Use it as your starting context and verify only the minimum files needed.\n\n"
            f"{context_text}\n\nTask:\n{task['prompt']}"
        )
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    turns = 0
    start = time.time()

    for _ in range(12):
        turns += 1
        response = gemini_call(api_key, model, contents, tool_schemas())
        usage = response.get("usageMetadata", {})
        prompt_tokens += usage.get("promptTokenCount", 0)
        completion_tokens += usage.get("candidatesTokenCount", 0)
        total_tokens += usage.get("totalTokenCount", 0)

        candidate = (response.get("candidates") or [{}])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            break

        model_parts = []
        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                name = fc["name"]
                args = fc.get("args", {})
                model_parts.append({"functionCall": {"name": name, "args": args}})

                if name == "list_files":
                    result = repo_tools.list_files(args.get("subpath", "."))
                elif name == "read_file":
                    result = repo_tools.read_file(
                        args["relative_path"],
                        int(args.get("start_line", 1)),
                        int(args.get("max_lines", 200)),
                    )
                elif name == "search_files":
                    result = repo_tools.search_files(args["query"], args.get("subpath", "."))
                elif name == "submit_answer":
                    elapsed = round(time.time() - start, 2)
                    return {
                        "task_id": task["id"],
                        "mode": "with_context" if context_text else "cold",
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "files_read_count": repo_tools.files_read,
                        "total_lines_read": repo_tools.total_lines_read,
                        "search_count": repo_tools.search_count,
                        "tool_calls": repo_tools.tool_calls,
                        "agent_turns": turns,
                        "elapsed_seconds": elapsed,
                        "answer": args.get("answer", ""),
                        "files_verified": args.get("files_verified", []),
                        "confidence": args.get("confidence", ""),
                    }
                else:
                    result = {"error": f"Unknown tool: {name}"}

                contents.append({"role": "model", "parts": model_parts})
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": name,
                                    "response": result,
                                }
                            }
                        ],
                    }
                )
                break
            elif "text" in part:
                text = part["text"].strip()
                if text:
                    elapsed = round(time.time() - start, 2)
                    return {
                        "task_id": task["id"],
                        "mode": "with_context" if context_text else "cold",
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "files_read_count": repo_tools.files_read,
                        "total_lines_read": repo_tools.total_lines_read,
                        "search_count": repo_tools.search_count,
                        "tool_calls": repo_tools.tool_calls,
                        "agent_turns": turns,
                        "elapsed_seconds": elapsed,
                        "answer": text,
                        "files_verified": [],
                        "confidence": "unspecified",
                    }

    elapsed = round(time.time() - start, 2)
    return {
        "task_id": task["id"],
        "mode": "with_context" if context_text else "cold",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "files_read_count": repo_tools.files_read,
        "total_lines_read": repo_tools.total_lines_read,
        "search_count": repo_tools.search_count,
        "tool_calls": repo_tools.tool_calls,
        "agent_turns": turns,
        "elapsed_seconds": elapsed,
        "answer": "No final answer submitted within turn limit.",
        "files_verified": [],
        "confidence": "low",
    }


def fetch_context(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "task_id",
        "mode",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "files_read_count",
        "total_lines_read",
        "search_count",
        "tool_calls",
        "agent_turns",
        "elapsed_seconds",
        "answer",
        "files_verified",
        "confidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["files_verified"] = ";".join(out.get("files_verified", []))
            writer.writerow(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-token agent-context benchmarks with Gemini.")
    parser.add_argument("--repo", required=True, help="Path to the target repository, e.g. demo-app")
    parser.add_argument("--tasks", default="benchmarks/tasks_demo_app.json", help="JSON task file")
    parser.add_argument("--context-file", help="Path to exported Halite markdown context")
    parser.add_argument("--context-url", help="URL to fetch exported Halite context")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name")
    parser.add_argument("--api-key", help="Gemini API key; defaults to GEMINI_API_KEY env var")
    parser.add_argument("--output", default="benchmarks/output/gemini_agent_benchmark.csv", help="CSV output path")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing Gemini API key. Pass --api-key or set GEMINI_API_KEY.")

    repo_root = Path(args.repo).resolve()
    tasks = json.loads(read_text(Path(args.tasks)))

    context_text = None
    if args.context_file:
        context_text = read_text(Path(args.context_file))
    elif args.context_url:
        context_text = fetch_context(args.context_url)

    rows = []
    for task in tasks:
        rows.append(run_task(api_key, args.model, repo_root, task, None))
        if context_text:
            rows.append(run_task(api_key, args.model, repo_root, task, context_text))

    write_csv(Path(args.output), rows)
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
