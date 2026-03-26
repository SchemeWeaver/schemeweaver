"""Semantic ID utilities."""
import re


def to_semantic_id(label: str) -> str:
    """Convert a label to a semantic kebab-case ID."""
    s = label.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def node_id(semantic: str) -> str:
    return f"node-{semantic}"


def edge_id(semantic: str) -> str:
    return f"edge-{semantic}"


def group_id(semantic: str) -> str:
    return f"group-{semantic}"
