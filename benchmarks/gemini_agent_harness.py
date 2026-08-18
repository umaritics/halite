import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"

SYSTEM_RULES = """You are benchmarking repository understanding.

Hard rules:
- You MUST inspect the repository with tools before answering.
- Do not answer from guesses or from Halite context alone.
- Halite context, if present, is only a map: use it to choose which files to open, then verify those files with read_file.
- Never inspect documents that are not in the target repository.
- After you have verified the minimum files, you MUST finish by calling submit_answer.
- Do not write a plan in plain text. Call a tool instead.
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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


def parse_tool_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def wait_from_rate_limit(exc: Exception) -> float:
    text = str(exc)
    match = re.search(r"try again in ([\d.]+)\s*(ms|s)", text, re.I)
    if match:
        value = float(match.group(1))
        seconds = value / 1000.0 if match.group(2).lower() == "ms" else value
        return max(seconds + 2.0, 3.0)
    return 8.0


_groq_client = None


def groq_sdk_call(api_key: str, model: str, messages: list, tools: list, force_tools: bool = True) -> dict:
    global _groq_client
    from groq import Groq

    if _groq_client is None:
        _groq_client = Groq(api_key=api_key)

    last_error = None
    for attempt in range(8):
        try:
            completion = _groq_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="required" if force_tools else "auto",
                temperature=0.2,
            )
            if hasattr(completion, "model_dump"):
                return completion.model_dump()
            return json.loads(completion.model_dump_json())
        except Exception as exc:
            last_error = exc
            name = type(exc).__name__
            text = str(exc)
            if "RateLimit" not in name and "429" not in text and "rate_limit" not in text:
                raise
            wait_s = wait_from_rate_limit(exc)
            print(f"Groq rate limit; waiting {wait_s:.1f}s (attempt {attempt + 1}/8)")
            time.sleep(wait_s)
    raise last_error


def groq_http_call(api_key: str, model: str, messages: list, tools: list, force_tools: bool = True) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "required" if force_tools else "auto",
        "temperature": 0.2,
    }
    body = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(6):
        request = urllib.request.Request(
            GROQ_URL,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "HaliteBenchmark/1.0 (compatible; groq-python)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            last_error = HTTPCallError(exc.code, detail)
            if exc.code not in {429, 500, 502, 503}:
                raise last_error from exc
            retry_after = exc.headers.get("Retry-After")
            wait_s = int(retry_after) if retry_after and retry_after.isdigit() else min(8 * (2 ** attempt), 60)
            print(f"Groq HTTP {exc.code}; retrying in {wait_s}s (attempt {attempt + 1}/6)")
            time.sleep(wait_s)
    raise last_error


def groq_call(api_key: str, model: str, messages: list, tools: list, force_tools: bool = True) -> dict:
    try:
        return groq_sdk_call(api_key, model, messages, tools, force_tools)
    except ImportError:
        return groq_http_call(api_key, model, messages, tools, force_tools)


class HTTPCallError(RuntimeError):
    def __init__(self, code: int, detail: str):
        super().__init__(f"Groq HTTP {code}: {detail[:500]}")
        self.code = code
        self.detail = detail


def tool_schemas() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List repository files under a subpath.",
                "parameters": {
                    "type": "object",
                    "properties": {"subpath": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file window with line numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "max_lines": {"type": "integer"},
                    },
                    "required": ["relative_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search for a text query across repository files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "subpath": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "submit_answer",
                "description": "Finish the task with your answer and the files you verified.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "files_verified": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "confidence": {"type": "string"},
                    },
                    "required": ["answer", "files_verified", "confidence"],
                },
            },
        },
    ]


def result_row(task: dict, context_text: str | None, repo_tools: RepoTools, turns: int, start: float, usage: dict, answer: str, files_verified: list, confidence: str) -> dict:
    return {
        "task_id": task["id"],
        "mode": "with_context" if context_text else "cold",
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "files_read_count": repo_tools.files_read,
        "total_lines_read": repo_tools.total_lines_read,
        "search_count": repo_tools.search_count,
        "tool_calls": repo_tools.tool_calls,
        "agent_turns": turns,
        "elapsed_seconds": round(time.time() - start, 2),
        "answer": answer,
        "files_verified": files_verified,
        "confidence": confidence,
    }


def run_task(api_key: str, model: str, repo_root: Path, task: dict, context_text: str | None) -> dict:
    repo_tools = RepoTools(repo_root)
    prompt = task["prompt"]
    if context_text:
        prompt = (
            "You are given a Halite project-memory export for THIS repository only.\n"
            "Use it to choose which files to open. Then verify those files with read_file.\n"
            "Do not open meeting transcripts or documents that are not in the repo.\n\n"
            f"{context_text}\n\nTask:\n{task['prompt']}"
        )
    messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {"role": "user", "content": prompt},
    ]

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    turns = 0
    start = time.time()
    tools = tool_schemas()

    for _ in range(12):
        turns += 1
        force_tools = repo_tools.files_read == 0
        response = groq_call(api_key, model, messages, tools, force_tools=force_tools)
        resp_usage = response.get("usage") or {}
        usage["prompt_tokens"] += resp_usage.get("prompt_tokens", 0)
        usage["completion_tokens"] += resp_usage.get("completion_tokens", 0)
        usage["total_tokens"] += resp_usage.get("total_tokens", 0)

        message = ((response.get("choices") or [{}])[0]).get("message") or {}
        tool_calls = message.get("tool_calls") or []
        text = (message.get("content") or "").strip()

        if not tool_calls:
            messages.append({"role": "assistant", "content": text or ""})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "That was a plan, not a verified answer. "
                        "Call list_files, search_files, or read_file next. "
                        "After inspecting files, call submit_answer."
                    ),
                }
            )
            continue

        messages.append(
            {
                "role": "assistant",
                "content": text or None,
                "tool_calls": tool_calls,
            }
        )

        finished = None
        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name", "")
            args = parse_tool_args(fn.get("arguments"))
            call_id = call.get("id") or name

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
                if repo_tools.files_read == 0:
                    result = {"error": "You must read at least one repository file before submit_answer."}
                else:
                    finished = args
                    result = {"status": "accepted"}
            else:
                result = {"error": f"Unknown tool: {name}"}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result),
                }
            )

        if finished:
            return result_row(
                task,
                context_text,
                repo_tools,
                turns,
                start,
                usage,
                finished.get("answer", ""),
                finished.get("files_verified", []),
                finished.get("confidence", ""),
            )

    return result_row(
        task,
        context_text,
        repo_tools,
        turns,
        start,
        usage,
        "No final answer submitted within turn limit.",
        [],
        "low",
    )


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
            out["files_verified"] = (
                out["files_verified"]
                if isinstance(out.get("files_verified"), str)
                else ";".join(out.get("files_verified") or [])
            )
            writer.writerow(out)


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def already_done(rows: list[dict], task_id: str, mode: str) -> bool:
    return any(row.get("task_id") == task_id and row.get("mode") == mode for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-token agent-context benchmarks with Groq.")
    parser.add_argument("--repo", required=True, help="Path to the target repository, e.g. demo-app")
    parser.add_argument("--tasks", default="benchmarks/tasks_demo_app.json", help="JSON task file")
    parser.add_argument("--context-file", help="Path to exported Halite markdown context")
    parser.add_argument("--context-url", help="URL to fetch exported Halite context")
    parser.add_argument("--model", default=DEFAULT_GROQ_MODEL, help="Groq model name")
    parser.add_argument("--api-key", help="Groq API key; defaults to GROQ_API_KEY or backend/.env")
    parser.add_argument("--output", default="benchmarks/output/groq_agent_benchmark.csv", help="CSV output path")
    parser.add_argument("--sleep", type=float, default=20.0, help="Seconds to wait between task runs")
    parser.add_argument("--resume", action="store_true", help="Skip task/mode pairs already in the output CSV")
    args = parser.parse_args()

    env_file = load_env_file(Path("backend/.env"))
    api_key = args.api_key or os.environ.get("GROQ_API_KEY") or env_file.get("GROQ_API_KEY")
    model = args.model or env_file.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    if not api_key:
        raise SystemExit("Missing Groq API key. Pass --api-key, set GROQ_API_KEY, or put it in backend/.env.")

    repo_root = Path(args.repo).resolve()
    tasks = json.loads(read_text(Path(args.tasks)))

    context_text = None
    if args.context_file:
        context_text = read_text(Path(args.context_file))
    elif args.context_url:
        context_text = fetch_context(args.context_url)

    output_path = Path(args.output)
    rows = load_csv(output_path) if args.resume else []
    if rows:
        print(f"Resuming with {len(rows)} existing row(s) from {output_path}")

    for task in tasks:
        if already_done(rows, task["id"], "cold"):
            print(f"Skipping {task['id']} cold (already in CSV)")
        else:
            if rows:
                time.sleep(args.sleep)
            print(f"Running {task['id']} cold...")
            rows.append(run_task(api_key, model, repo_root, task, None))
            write_csv(output_path, rows)
        if context_text:
            if already_done(rows, task["id"], "with_context"):
                print(f"Skipping {task['id']} with_context (already in CSV)")
            else:
                time.sleep(args.sleep)
                print(f"Running {task['id']} with_context...")
                rows.append(run_task(api_key, model, repo_root, task, context_text))
                write_csv(output_path, rows)

    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
