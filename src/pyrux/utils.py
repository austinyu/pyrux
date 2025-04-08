

def join_path(head: str | None, tail: str) -> str:
    return f"{head}.{tail}" if head else tail

def join_action(path: str, action: str) -> str:
    return f"{path}::{action}"
