def check_invalidation(commit_sha: str, changed_files: list, graph_repo) -> list[dict]:
    """Flag active decisions when their linked components' files change."""
    return graph_repo.invalidate_decisions_for_files(commit_sha, changed_files)
