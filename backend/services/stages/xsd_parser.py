"""XSD Parser — Stage implementation for XSD parsing and FieldTree construction.

Parses an XSD schema file using lxml, navigating xs:schema → xs:element →
xs:complexType → xs:sequence, and returns a FieldTree with dot-separated
paths, type information, and array/optional flags.

Raises ValueError (with a human-readable message) if the XSD is syntactically
invalid.  This causes the pipeline to mark the stage as failed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.field_tree import FieldNode, FieldTree, map_xsd_type

# ---------------------------------------------------------------------------
# XML namespace helpers
# ---------------------------------------------------------------------------

_XSD_NAMESPACES = (
    "{http://www.w3.org/2001/XMLSchema}",
    "{http://www.w3.org/1999/XMLSchema}",  # legacy variant
)

# Tag shortcuts
_TAG_SCHEMA = [ns + "schema" for ns in _XSD_NAMESPACES]
_TAG_ELEMENT = [ns + "element" for ns in _XSD_NAMESPACES]
_TAG_COMPLEX_TYPE = [ns + "complexType" for ns in _XSD_NAMESPACES]
_TAG_SEQUENCE = [ns + "sequence" for ns in _XSD_NAMESPACES]
_TAG_ALL = [ns + "all" for ns in _XSD_NAMESPACES]
_TAG_CHOICE = [ns + "choice" for ns in _XSD_NAMESPACES]
_TAG_SIMPLE_TYPE = [ns + "simpleType" for ns in _XSD_NAMESPACES]
_TAG_RESTRICTION = [ns + "restriction" for ns in _XSD_NAMESPACES]
_TAG_EXTENSION = [ns + "extension" for ns in _XSD_NAMESPACES]
_TAG_COMPLEX_CONTENT = [ns + "complexContent" for ns in _XSD_NAMESPACES]
_TAG_SIMPLE_CONTENT = [ns + "simpleContent" for ns in _XSD_NAMESPACES]


def _is_tag(element: Any, tag_list: List[str]) -> bool:
    return element.tag in tag_list


def _strip_ns(tag: str) -> str:
    """Return the local name of an XML tag, stripping any namespace URI."""
    if "}" in tag:
        return tag.split("}")[-1]
    return tag


# ---------------------------------------------------------------------------
# Core XSD parsing logic
# ---------------------------------------------------------------------------


class _XsdParser:
    """Internal stateful parser for a single XSD document."""

    def __init__(self, root: Any) -> None:
        self._root = root
        # Pre-index globally defined complex types by name for reference resolution
        self._global_complex_types: Dict[str, Any] = {}
        self._collect_global_complex_types()

    def _collect_global_complex_types(self) -> None:
        """Index all top-level xs:complexType elements by their ``name``."""
        for child in self._root:
            if _is_tag(child, _TAG_COMPLEX_TYPE):
                name = child.get("name")
                if name:
                    self._global_complex_types[name] = child

    # --- Element → FieldNode -----------------------------------------------

    def _parse_element(
        self,
        element: Any,
        parent_path: str,
    ) -> Optional[FieldNode]:
        """Convert a single xs:element to a FieldNode (recursive)."""
        name = element.get("name")
        if not name:
            # Ignore anonymous or ref-only elements we cannot name
            return None

        path = f"{parent_path}.{name}" if parent_path else name

        # --- Determine is_array (maxOccurs) ---------------------------------
        max_occurs = element.get("maxOccurs", "1")
        is_array = max_occurs == "unbounded" or (
            max_occurs.isdigit() and int(max_occurs) > 1
        )

        # --- Determine required (minOccurs) ----------------------------------
        min_occurs = element.get("minOccurs", "1")
        required = min_occurs != "0"

        # --- Determine type + children --------------------------------------
        type_attr = element.get("type")
        children: List[FieldNode] = []

        if type_attr is not None:
            # Simple or global complex type reference
            field_type = map_xsd_type(type_attr)
            if field_type == "complex":
                # Try to resolve the referenced global complex type
                # Strip any prefix from type_attr to get the local name
                local_type = type_attr.split(":")[-1] if ":" in type_attr else type_attr
                global_ct = self._global_complex_types.get(local_type)
                if global_ct is not None:
                    children = self._parse_complex_type_children(global_ct, path)
        else:
            # Inline complex type or simple type
            complex_type = self._find_child(element, _TAG_COMPLEX_TYPE)
            simple_type = self._find_child(element, _TAG_SIMPLE_TYPE)

            if complex_type is not None:
                field_type = "complex"
                children = self._parse_complex_type_children(complex_type, path)
            elif simple_type is not None:
                # Extract base type from restriction/extension
                field_type = self._extract_simple_type(simple_type)
            else:
                # No type info at all — treat as string leaf
                field_type = "string"

        return FieldNode(
            name=name,
            path=path,
            type=field_type,
            required=required,
            is_array=is_array,
            children=children,
        )

    def _parse_complex_type_children(
        self, complex_type: Any, parent_path: str
    ) -> List[FieldNode]:
        """Parse children of a complexType element (handles complexContent too)."""
        # Look for sequence / all / choice directly under complexType
        for container_tag in (_TAG_SEQUENCE, _TAG_ALL, _TAG_CHOICE):
            container = self._find_child(complex_type, container_tag)
            if container is not None:
                return self._parse_container_children(container, parent_path)

        # complexContent → extension or restriction
        complex_content = self._find_child(complex_type, _TAG_COMPLEX_CONTENT)
        if complex_content is not None:
            for ext_tag in (_TAG_EXTENSION, _TAG_RESTRICTION):
                ext = self._find_child(complex_content, ext_tag)
                if ext is not None:
                    return self._parse_complex_type_children(ext, parent_path)

        # simpleContent — leaf with simple type base, no children
        return []

    def _parse_container_children(
        self, container: Any, parent_path: str
    ) -> List[FieldNode]:
        """Parse xs:element children within a sequence/all/choice container."""
        children: List[FieldNode] = []
        for child in container:
            if _is_tag(child, _TAG_ELEMENT):
                node = self._parse_element(child, parent_path)
                if node is not None:
                    children.append(node)
        return children

    def _extract_simple_type(self, simple_type: Any) -> str:
        """Extract the canonical type from an inline xs:simpleType."""
        for child in simple_type:
            if _is_tag(child, _TAG_RESTRICTION):
                base = child.get("base")
                return map_xsd_type(base)
            if _is_tag(child, _TAG_EXTENSION):
                base = child.get("base")
                return map_xsd_type(base)
        return "string"

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _find_child(element: Any, tag_list: List[str]) -> Optional[Any]:
        for child in element:
            if _is_tag(child, tag_list):
                return child
        return None

    # --- Public entry point -------------------------------------------------

    def parse(self) -> FieldTree:
        """Walk the xs:schema root and return a FieldTree.

        When the schema has a single top-level wrapper element (the common
        pattern: <xs:element name="documento">…</xs:element>), its direct
        children are promoted to root_nodes so that paths start at the semantic
        top level (e.g. ``cliente``, ``movimentos``) rather than at the wrapper
        (``documento.cliente``).  This matches the expected output in Dev Notes.

        Schemas with multiple top-level elements are kept as-is.
        """
        top_level_elements = [
            child for child in self._root if _is_tag(child, _TAG_ELEMENT)
        ]

        if len(top_level_elements) == 1:
            # Single wrapper element — skip it, parse children directly at root
            wrapper = top_level_elements[0]
            complex_type = self._find_child(wrapper, _TAG_COMPLEX_TYPE)
            if complex_type is not None:
                root_nodes = self._parse_complex_type_children(complex_type, "")
            else:
                # Fallback: parse the wrapper itself
                node = self._parse_element(wrapper, "")
                root_nodes = [node] if node else []
        else:
            # Multiple top-level elements — expose them all as roots
            root_nodes = []
            for el in top_level_elements:
                node = self._parse_element(el, "")
                if node is not None:
                    root_nodes.append(node)

        return FieldTree.from_root_nodes(root_nodes)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_xsd(xsd_source: "str | bytes | Path") -> FieldTree:
    """Parse an XSD schema and return a FieldTree.

    Args:
        xsd_source: An XSD file path (Path or str), or raw XSD bytes/string.

    Returns:
        A FieldTree with root_nodes and flat_paths populated.

    Raises:
        ValueError: If the XSD is syntactically invalid (wraps
                    lxml.etree.XMLSyntaxError with a human-readable message).
        FileNotFoundError: If xsd_source is a path that does not exist.
    """
    try:
        from lxml import etree
    except ImportError as exc:
        raise ImportError(
            "lxml is required for XSD parsing. Install with: pip install lxml"
        ) from exc

    # --- Load the XML document ---------------------------------------------
    try:
        if isinstance(xsd_source, Path):
            xsd_source = str(xsd_source)

        if isinstance(xsd_source, str):
            # Could be a file path or an inline XML string
            src = xsd_source.strip()
            if src.startswith("<"):
                # Inline XML string
                raw_bytes = src.encode("utf-8")
                root = etree.fromstring(raw_bytes)
            else:
                # File path
                tree = etree.parse(src)
                root = tree.getroot()
        else:
            # bytes
            root = etree.fromstring(xsd_source)

    except etree.XMLSyntaxError as exc:
        line = getattr(exc, "lineno", None)
        line_info = f" na linha {line}" if line else ""
        raise ValueError(
            f"Erro de parse XSD: {exc.msg}{line_info}"
        ) from exc
    except OSError as exc:
        raise FileNotFoundError(f"Arquivo XSD não encontrado: {xsd_source}") from exc

    # --- Delegate to internal parser ---------------------------------------
    parser = _XsdParser(root)
    return parser.parse()


# ---------------------------------------------------------------------------
# Stage executor (for pipeline integration)
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage executor — XSD Parsing.

    Reads context["xsd_path"] (str or Path) and writes context["field_tree"]
    with the serialized FieldTree dict, plus SSE-compatible progress markers.

    Returns a result dict for the orchestrator.
    """
    xsd_path = context.get("xsd_path")

    # SSE-style progress emit (fire-and-forget; orchestrator listens for these)
    context.setdefault("_sse_events", [])
    context["_sse_events"].append({"stage": "xsd_parsing", "status": "started"})

    await asyncio.sleep(0)  # yield to event loop

    if not xsd_path:
        context["_sse_events"].append({"stage": "xsd_parsing", "status": "skipped", "reason": "no xsd_path"})
        context["field_tree"] = None
        return {"xsd_parsed": False, "reason": "no xsd_path in context"}

    try:
        field_tree = parse_xsd(xsd_path)
    except (ValueError, FileNotFoundError) as exc:
        context["_sse_events"].append({"stage": "xsd_parsing", "status": "failed", "error": str(exc)})
        context["field_tree"] = None
        context["xsd_parse_error"] = str(exc)
        raise  # Propagate so orchestrator marks stage as failed

    context["field_tree"] = field_tree.to_dict()
    context["_sse_events"].append({
        "stage": "xsd_parsing",
        "status": "completed",
        "field_count": len(field_tree.flat_paths),
    })

    return {
        "xsd_parsed": True,
        "root_count": len(field_tree.root_nodes),
        "field_count": len(field_tree.flat_paths),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry: Any) -> None:
    """Register the XSD Parsing stage in the given StageRegistry.

    Uses stage_number=29 (Block 1 / Aquisição extension) so it does not
    conflict with the existing pipeline.  Stage 28 is reserved for
    Pipeline Result (Block 8).
    """
    # Remove any existing stub with this number (idempotent)
    registry.remove_stage(29)

    # Ensure Block 1 exists (Aquisição)
    if registry.get_block(1) is None:
        registry.register_block(1, "Aquisição")

    registry.register_stage(
        stage_number=29,
        name="XSD Parsing",
        block_id=1,
        estimated_duration=0.5,
        execute_fn=execute,
    )
