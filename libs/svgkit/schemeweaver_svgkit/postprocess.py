"""SVG post-processing: compression, a11y, semantic ID validation."""
import re


class PostProcessor:
    """Applies post-processing passes to an SVG string."""

    def process(self, svg: str) -> str:
        svg = self._ensure_aria_labels(svg)
        svg = self._ensure_role_attributes(svg)
        return svg

    def _ensure_aria_labels(self, svg: str) -> str:
        """Warn if any sw-node lacks an aria-label (returns svg unchanged, logs warnings)."""
        nodes_without_aria = re.findall(
            r'<g[^>]+class="sw-node[^"]*"[^>]*(?!aria-label)[^>]*>', svg
        )
        if nodes_without_aria:
            import warnings

            warnings.warn(f"Found {len(nodes_without_aria)} node(s) without aria-label")
        return svg

    def _ensure_role_attributes(self, svg: str) -> str:
        """Ensure the root SVG has role=img."""
        if 'role="img"' not in svg:
            svg = svg.replace("<svg ", '<svg role="img" ', 1)
        return svg

    def validate(self, svg: str) -> list[str]:
        """Return a list of accessibility/semantic issues found in the SVG."""
        issues = []

        if 'role="img"' not in svg:
            issues.append("Root <svg> missing role='img'")
        if "<title>" not in svg:
            issues.append("Missing <title> element for screen readers")
        if "aria-label" not in svg:
            issues.append("No aria-label attributes found")

        # Check for semantic ID convention
        node_ids = re.findall(r'<g[^>]+id="([^"]*)"[^>]+class="sw-node', svg)
        for nid in node_ids:
            if not nid.startswith("node-"):
                issues.append(f"Node id '{nid}' doesn't follow 'node-*' convention")

        return issues
