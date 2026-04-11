"""Repo Analyzer — walks a local or remote codebase and compiles a markdown Knowledge Base."""
from __future__ import annotations

import subprocess
import tempfile
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Directories / files to ignore when walking ────────────────────────────────

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache",
    "target", "dist", "build", ".next", ".nuxt", ".output", ".vercel",
    "venv", ".venv", "env", ".env", ".tox",
}

_SKIP_SUFFIXES = {".egg-info"}

# Manifest files — read these in full (up to _MANIFEST_LINE_LIMIT lines)
_MANIFESTS = [
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile",
    "composer.json",
    "mix.exs",
]

_MANIFEST_LINE_LIMIT = 80

# Docker / infra files
_INFRA_FILES = [
    "docker-compose.yml", "docker-compose.yaml",
    "docker-compose.dev.yml", "docker-compose.prod.yml",
    "Dockerfile",
]

# Env sample files
_ENV_SAMPLES = [".env.example", ".env.sample", ".env.template", ".env.local.example"]


# ── KnowledgeBase dataclass ───────────────────────────────────────────────────

@dataclass
class ServiceInfo:
    name: str
    path: str            # relative path inside repo
    manifest_type: str   # e.g. "pyproject.toml", "package.json"
    key_deps: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class KnowledgeBase:
    repo_name: str
    source: str                              # original path or URL
    overview: str                            # README excerpt
    structure: str                           # annotated directory tree
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    services: list[ServiceInfo] = field(default_factory=list)
    runtime_deps: list[str] = field(default_factory=list)
    infrastructure: list[str] = field(default_factory=list)
    env_keys: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# Knowledge Base: {self.repo_name}")
        lines.append(f"> Source: {self.source}")
        lines.append("")

        if self.overview:
            lines.append("## Overview")
            lines.append(self.overview)
            lines.append("")

        if self.structure:
            lines.append("## Repository Structure")
            lines.append("```")
            lines.append(self.structure)
            lines.append("```")
            lines.append("")

        if self.languages or self.frameworks:
            lines.append("## Tech Stack")
            if self.languages:
                lines.append(f"- Languages: {', '.join(self.languages)}")
            if self.frameworks:
                lines.append(f"- Frameworks / Runtimes: {', '.join(self.frameworks)}")
            lines.append("")

        if self.services:
            lines.append("## Services & Modules")
            for svc in self.services:
                lines.append(f"### {svc.name} (`{svc.path}`)")
                if svc.description:
                    lines.append(svc.description)
                lines.append(f"Manifest: `{svc.manifest_type}`")
                if svc.key_deps:
                    lines.append(f"Key dependencies: {', '.join(svc.key_deps[:20])}")
                lines.append("")

        if self.runtime_deps:
            lines.append("## Runtime Dependencies")
            for dep in self.runtime_deps[:40]:
                lines.append(f"- {dep}")
            lines.append("")

        if self.infrastructure:
            lines.append("## Infrastructure")
            for item in self.infrastructure:
                lines.append(f"- {item}")
            lines.append("")

        if self.env_keys:
            lines.append("## Configuration")
            lines.append("Key environment variables / config keys:")
            for key in self.env_keys[:30]:
                lines.append(f"- `{key}`")
            lines.append("")

        return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_git_url(source: str) -> bool:
    return source.startswith(("http://", "https://", "git@", "git://", "ssh://"))


def _safe_read(path: Path, max_lines: int = 100) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def _should_skip(p: Path) -> bool:
    if p.name in _SKIP_DIRS:
        return True
    for suffix in _SKIP_SUFFIXES:
        if p.name.endswith(suffix):
            return True
    return False


def _build_tree(root: Path, max_depth: int = 3, _depth: int = 0, _prefix: str = "") -> list[str]:
    if _depth > max_depth:
        return []
    lines: list[str] = []
    try:
        children = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return []

    visible = [c for c in children if not _should_skip(c)]
    for i, child in enumerate(visible):
        connector = "└── " if i == len(visible) - 1 else "├── "
        lines.append(f"{_prefix}{connector}{child.name}")
        if child.is_dir() and _depth < max_depth:
            extension = "    " if i == len(visible) - 1 else "│   "
            lines.extend(_build_tree(child, max_depth, _depth + 1, _prefix + extension))
    return lines


def _extract_python_deps(toml_text: str) -> tuple[list[str], list[str]]:
    """Return (frameworks, runtime_deps) from pyproject.toml content."""
    frameworks: list[str] = []
    deps: list[str] = []
    in_deps = False
    _FRAMEWORK_HINTS = {
        "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
        "starlette": "Starlette", "litestar": "Litestar",
        "sqlalchemy": "SQLAlchemy", "alembic": "Alembic",
        "pydantic": "Pydantic", "uvicorn": "Uvicorn",
        "celery": "Celery", "arq": "ARQ", "redis": "Redis",
        "anthropic": "Anthropic SDK", "openai": "OpenAI SDK",
        "torch": "PyTorch", "transformers": "HuggingFace Transformers",
    }
    for line in toml_text.splitlines():
        stripped = line.strip()
        if stripped in ("[project.dependencies]", "dependencies = ["):
            in_deps = True
            continue
        if in_deps and stripped.startswith("[") and stripped != "[":
            in_deps = False
        if in_deps or "dependencies" in line.lower():
            # Extract package names from lines like '"fastapi>=0.100",'
            import re
            for match in re.finditer(r'["\']([A-Za-z0-9_\-]+)', line):
                name = match.group(1).lower()
                if name and not name.startswith("-"):
                    deps.append(name)
                    hint = _FRAMEWORK_HINTS.get(name)
                    if hint and hint not in frameworks:
                        frameworks.append(hint)
    return frameworks, list(dict.fromkeys(deps))


def _extract_node_deps(pkg_text: str) -> tuple[list[str], list[str], str]:
    """Return (frameworks, runtime_deps, description) from package.json content."""
    import json as _json
    frameworks: list[str] = []
    deps: list[str] = []
    description = ""
    _FRAMEWORK_HINTS = {
        "vue": "Vue 3", "nuxt": "Nuxt", "react": "React", "next": "Next.js",
        "express": "Express", "fastify": "Fastify", "hono": "Hono",
        "vite": "Vite", "webpack": "Webpack",
        "prisma": "Prisma", "drizzle-orm": "Drizzle ORM",
        "typeorm": "TypeORM", "mongoose": "Mongoose",
        "@anthropic-ai/sdk": "Anthropic SDK", "openai": "OpenAI SDK",
        "tailwindcss": "Tailwind CSS",
    }
    try:
        data = _json.loads(pkg_text)
        description = data.get("description", "")
        all_deps = {**data.get("dependencies", {}), **data.get("peerDependencies", {})}
        for pkg in all_deps:
            deps.append(pkg)
            hint = _FRAMEWORK_HINTS.get(pkg.lower())
            if hint and hint not in frameworks:
                frameworks.append(hint)
    except Exception:
        pass
    return frameworks, deps, description


def _extract_cargo_deps(toml_text: str) -> tuple[list[str], list[str]]:
    """Return (frameworks, runtime_deps) from Cargo.toml content."""
    frameworks: list[str] = []
    deps: list[str] = []
    _FRAMEWORK_HINTS = {
        "tokio": "Tokio", "axum": "Axum", "actix-web": "Actix-web",
        "warp": "Warp", "reqwest": "reqwest", "serde": "Serde",
        "sqlx": "SQLx", "diesel": "Diesel",
        "clap": "clap CLI", "anyhow": "anyhow", "tracing": "tracing",
    }
    in_deps = False
    import re
    for line in toml_text.splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
        if in_deps:
            m = re.match(r'^([a-zA-Z0-9_\-]+)\s*=', stripped)
            if m:
                name = m.group(1).lower()
                deps.append(name)
                hint = _FRAMEWORK_HINTS.get(name)
                if hint and hint not in frameworks:
                    frameworks.append(hint)
    return frameworks, deps


def _extract_go_info(gomod_text: str) -> tuple[list[str], list[str]]:
    """Return (frameworks, runtime_deps) from go.mod content."""
    frameworks: list[str] = []
    deps: list[str] = []
    _FRAMEWORK_HINTS = {
        "gin-gonic/gin": "Gin", "labstack/echo": "Echo",
        "gofiber/fiber": "Fiber", "go-chi/chi": "Chi",
        "gorilla/mux": "Gorilla Mux",
        "gorm.io/gorm": "GORM", "go-redis/redis": "go-redis",
        "golang-migrate": "golang-migrate",
    }
    in_require = False
    import re
    for line in gomod_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
        if in_require or stripped.startswith("require "):
            m = re.search(r'(\S+/\S+)\s+v', stripped)
            if m:
                pkg = m.group(1)
                deps.append(pkg)
                for hint_key, hint_val in _FRAMEWORK_HINTS.items():
                    if hint_key in pkg and hint_val not in frameworks:
                        frameworks.append(hint_val)
    return frameworks, deps


def _extract_docker_services(compose_text: str) -> list[str]:
    """Extract service names from docker-compose.yml."""
    services: list[str] = []
    in_services = False
    import re
    for line in compose_text.splitlines():
        stripped = line.strip()
        if stripped == "services:":
            in_services = True
            continue
        if in_services and re.match(r'^[a-zA-Z]', line) and stripped.endswith(":"):
            # Top-level key that's not indented — exit services block
            in_services = False
        if in_services:
            m = re.match(r'^  ([a-zA-Z0-9_\-]+):', line)
            if m:
                services.append(m.group(1))
    return services


def _extract_env_keys(env_text: str) -> list[str]:
    """Extract variable names from .env.example."""
    keys: list[str] = []
    import re
    for line in env_text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        m = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', line)
        if m:
            keys.append(m.group(1))
    return keys


# ── RepoAnalyzer ──────────────────────────────────────────────────────────────

class RepoAnalyzer:
    """Analyzes a local directory or git repository and compiles a KnowledgeBase."""

    def analyze(self, source: str) -> KnowledgeBase:
        """Analyze a local path or git URL and return a KnowledgeBase."""
        if _is_git_url(source):
            return self._analyze_url(source)
        return self._analyze_path(Path(source), source)

    def _analyze_url(self, url: str) -> KnowledgeBase:
        if not shutil.which("git"):
            raise RuntimeError("git is not available on PATH — cannot clone repository")
        tmp = tempfile.mkdtemp(prefix="sw-repo-")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", "--", url, tmp],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
            return self._analyze_path(Path(tmp), url)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _analyze_path(self, root: Path, source: str) -> KnowledgeBase:
        root = root.resolve()
        repo_name = root.name

        # 1. README
        overview = ""
        for readme_name in ("README.md", "README.rst", "README.txt", "README"):
            readme = root / readme_name
            if readme.exists():
                overview = _safe_read(readme, max_lines=60)
                break

        # 2. Directory tree
        tree_lines = [repo_name + "/"] + _build_tree(root, max_depth=2)
        structure = "\n".join(tree_lines)

        # 3. Find all manifests
        all_frameworks: list[str] = []
        all_runtime_deps: list[str] = []
        all_languages: list[str] = []
        services: list[ServiceInfo] = []

        # Collect manifests at root and one level deep (monorepo support)
        search_paths = [root] + [p for p in root.iterdir() if p.is_dir() and not _should_skip(p)]

        for search_dir in search_paths:
            for manifest_name in _MANIFESTS:
                manifest_path = search_dir / manifest_name
                if not manifest_path.exists():
                    continue
                rel = manifest_path.relative_to(root)
                text = _safe_read(manifest_path, _MANIFEST_LINE_LIMIT)
                svc_name = search_dir.name if search_dir != root else repo_name
                svc_path = str(rel.parent) if str(rel.parent) != "." else "."

                if manifest_name == "pyproject.toml":
                    if "Python" not in all_languages:
                        all_languages.append("Python")
                    fws, deps = _extract_python_deps(text)
                    for f in fws:
                        if f not in all_frameworks:
                            all_frameworks.append(f)
                    all_runtime_deps.extend(deps)
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path,
                        manifest_type="pyproject.toml", key_deps=deps[:10],
                    ))

                elif manifest_name == "requirements.txt":
                    if "Python" not in all_languages:
                        all_languages.append("Python")
                    deps = [
                        line.split("==")[0].split(">=")[0].split("[")[0].strip()
                        for line in text.splitlines()
                        if line.strip() and not line.startswith("#")
                    ]
                    all_runtime_deps.extend(deps)
                    # Only add as service if no pyproject.toml already found for this dir
                    if not any(s.path == svc_path and s.manifest_type == "pyproject.toml" for s in services):
                        services.append(ServiceInfo(
                            name=svc_name, path=svc_path,
                            manifest_type="requirements.txt", key_deps=deps[:10],
                        ))

                elif manifest_name == "package.json":
                    if "TypeScript" not in all_languages and "JavaScript" not in all_languages:
                        all_languages.append("TypeScript/JavaScript")
                    fws, deps, desc = _extract_node_deps(text)
                    for f in fws:
                        if f not in all_frameworks:
                            all_frameworks.append(f)
                    all_runtime_deps.extend(deps)
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path,
                        manifest_type="package.json", key_deps=deps[:10],
                        description=desc,
                    ))

                elif manifest_name == "Cargo.toml":
                    if "Rust" not in all_languages:
                        all_languages.append("Rust")
                    fws, deps = _extract_cargo_deps(text)
                    for f in fws:
                        if f not in all_frameworks:
                            all_frameworks.append(f)
                    all_runtime_deps.extend(deps)
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path,
                        manifest_type="Cargo.toml", key_deps=deps[:10],
                    ))

                elif manifest_name == "go.mod":
                    if "Go" not in all_languages:
                        all_languages.append("Go")
                    fws, deps = _extract_go_info(text)
                    for f in fws:
                        if f not in all_frameworks:
                            all_frameworks.append(f)
                    all_runtime_deps.extend(deps)
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path,
                        manifest_type="go.mod", key_deps=deps[:10],
                    ))

                elif manifest_name in ("pom.xml", "build.gradle", "build.gradle.kts"):
                    if "Java/Kotlin" not in all_languages:
                        all_languages.append("Java/Kotlin")
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path, manifest_type=manifest_name,
                    ))

                elif manifest_name == "Gemfile":
                    if "Ruby" not in all_languages:
                        all_languages.append("Ruby")
                    services.append(ServiceInfo(
                        name=svc_name, path=svc_path, manifest_type="Gemfile",
                    ))

        # Deduplicate services by path
        seen_paths: set[str] = set()
        deduped_services: list[ServiceInfo] = []
        for svc in services:
            if svc.path not in seen_paths:
                seen_paths.add(svc.path)
                deduped_services.append(svc)

        # 4. Infrastructure
        infrastructure: list[str] = []
        for infra_name in _INFRA_FILES:
            infra_path = root / infra_name
            if not infra_path.exists():
                continue
            if "docker-compose" in infra_name:
                text = _safe_read(infra_path, 200)
                svcs = _extract_docker_services(text)
                if svcs:
                    infrastructure.append(f"Docker Compose services: {', '.join(svcs)}")
                else:
                    infrastructure.append(f"Docker Compose: {infra_name}")
            elif infra_name == "Dockerfile":
                infrastructure.append("Dockerfile present")

        # Also check for k8s manifests
        k8s_dirs = [root / d for d in ("k8s", "kubernetes", "deploy", "infra", "charts")]
        for k8s_dir in k8s_dirs:
            if k8s_dir.is_dir():
                infrastructure.append(f"Kubernetes manifests: {k8s_dir.name}/")
                break

        # 5. Env keys
        env_keys: list[str] = []
        for env_name in _ENV_SAMPLES:
            env_path = root / env_name
            if env_path.exists():
                env_keys = _extract_env_keys(_safe_read(env_path, 100))
                break

        # Deduplicate runtime deps
        all_runtime_deps = list(dict.fromkeys(d for d in all_runtime_deps if d))

        return KnowledgeBase(
            repo_name=repo_name,
            source=source,
            overview=overview,
            structure=structure,
            languages=all_languages,
            frameworks=all_frameworks,
            services=deduped_services,
            runtime_deps=all_runtime_deps,
            infrastructure=infrastructure,
            env_keys=env_keys,
        )
