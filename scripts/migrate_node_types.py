"""
Migrate DIR JSON files from legacy vendor-prefixed node types to the new
vendor-agnostic schema (node_type + vendor + technology).

Usage:
    uv run python scripts/migrate_node_types.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

LEGACY_MAP: dict[str, tuple[str, str | None, str | None]] = {
    "aws.api_gateway":  ("gateway",    "aws", "api-gateway"),
    "aws.lambda":       ("service",    "aws", "lambda"),
    "aws.rds":          ("database",   "aws", "rds"),
    "aws.s3":           ("file-store", "aws", "s3"),
    "aws.ec2":          ("service",    "aws", "ec2"),
    "aws.elasticache":  ("cache",      "aws", "elasticache"),
    "storage":          ("file-store", None,  None),
}

VALID_NODE_TYPES = {
    "generic", "user", "service", "api", "gateway",
    "database", "document-store", "cache", "queue", "stream",
    "file-store", "search", "cdn", "auth", "monitor",
}


def migrate_node(node: dict) -> bool:
    """Mutate a node dict in-place. Returns True if changed."""
    changed = False
    raw_type = node.get("node_type", "generic")

    if raw_type in LEGACY_MAP:
        new_type, vendor, tech = LEGACY_MAP[raw_type]
        node["node_type"] = new_type
        if vendor and not node.get("vendor"):
            node["vendor"] = vendor
        if tech and not node.get("technology"):
            node["technology"] = tech
        changed = True
    elif raw_type not in VALID_NODE_TYPES:
        node["node_type"] = "generic"
        changed = True

    # Strip stale complexity field
    if "complexity" in node:
        del node["complexity"]
        changed = True

    for child in node.get("children", []):
        if migrate_node(child):
            changed = True

    return changed


def migrate_dir(data: dict) -> bool:
    """Mutate a DIR dict in-place. Returns True if changed."""
    changed = False

    # Strip stale top-level fields
    for stale in ("complexity_levels",):
        if stale in data:
            del data[stale]
            changed = True

    for node in data.get("nodes", []):
        if migrate_node(node):
            changed = True

    for edge in data.get("edges", []):
        if "complexity" in edge:
            del edge["complexity"]
            changed = True

    for group in data.get("groups", []):
        if "complexity" in group:
            del group["complexity"]
            changed = True

    return changed


def migrate_file(path: Path) -> bool:
    """Load, migrate, and save a JSON file if needed. Returns True if changed."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  SKIP  {path.relative_to(ROOT)} ({e})")
        return False

    changed = False

    # system.json files embed DIR inside views[].dir
    if "views" in data:
        for view in data.get("views", []):
            d = view.get("dir")
            if isinstance(d, dict):
                if migrate_dir(d):
                    changed = True
    # diagram.dir.json files are DIR directly (nodes must be a list)
    elif isinstance(data.get("nodes"), list):
        changed = migrate_dir(data)

    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  OK    {path.relative_to(ROOT)}")
    else:
        print(f"  SKIP  {path.relative_to(ROOT)} (no changes)")

    return changed


def main():
    targets = list((ROOT / "data").rglob("*.json"))
    if not targets:
        print("No JSON files found under data/")
        sys.exit(0)

    changed = 0
    for path in sorted(targets):
        if migrate_file(path):
            changed += 1

    print(f"\nMigrated {changed}/{len(targets)} files.")


if __name__ == "__main__":
    main()
