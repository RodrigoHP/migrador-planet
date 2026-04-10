"""FieldNode and FieldTree models for XSD-derived field hierarchies.

FieldTree represents the hierarchical structure of fields extracted from an XSD
schema, with dot-separated paths, type information, and array/optional flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Field type constants
# ---------------------------------------------------------------------------

FIELD_TYPE_STRING = "string"
FIELD_TYPE_DECIMAL = "decimal"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_INTEGER = "integer"
FIELD_TYPE_BOOLEAN = "boolean"
FIELD_TYPE_COMPLEX = "complex"

# Mapping from XSD built-in type local names → canonical type string
_XSD_TYPE_MAP: dict[str, str] = {
    "string": FIELD_TYPE_STRING,
    "normalizedString": FIELD_TYPE_STRING,
    "token": FIELD_TYPE_STRING,
    "anyURI": FIELD_TYPE_STRING,
    "QName": FIELD_TYPE_STRING,
    "NMTOKEN": FIELD_TYPE_STRING,
    "Name": FIELD_TYPE_STRING,
    "NCName": FIELD_TYPE_STRING,
    "ID": FIELD_TYPE_STRING,
    "IDREF": FIELD_TYPE_STRING,
    "language": FIELD_TYPE_STRING,
    "decimal": FIELD_TYPE_DECIMAL,
    "float": FIELD_TYPE_DECIMAL,
    "double": FIELD_TYPE_DECIMAL,
    "date": FIELD_TYPE_DATE,
    "dateTime": FIELD_TYPE_DATE,
    "time": FIELD_TYPE_DATE,
    "gYear": FIELD_TYPE_DATE,
    "gMonth": FIELD_TYPE_DATE,
    "gDay": FIELD_TYPE_DATE,
    "integer": FIELD_TYPE_INTEGER,
    "int": FIELD_TYPE_INTEGER,
    "long": FIELD_TYPE_INTEGER,
    "short": FIELD_TYPE_INTEGER,
    "byte": FIELD_TYPE_INTEGER,
    "positiveInteger": FIELD_TYPE_INTEGER,
    "nonNegativeInteger": FIELD_TYPE_INTEGER,
    "negativeInteger": FIELD_TYPE_INTEGER,
    "nonPositiveInteger": FIELD_TYPE_INTEGER,
    "unsignedInt": FIELD_TYPE_INTEGER,
    "unsignedLong": FIELD_TYPE_INTEGER,
    "unsignedShort": FIELD_TYPE_INTEGER,
    "unsignedByte": FIELD_TYPE_INTEGER,
    "boolean": FIELD_TYPE_BOOLEAN,
    "base64Binary": FIELD_TYPE_STRING,
    "hexBinary": FIELD_TYPE_STRING,
}


def map_xsd_type(xsd_type_name: str | None) -> str:
    """Map an XSD type name (with or without namespace prefix) to a canonical type.

    Examples:
        "xs:string"  → "string"
        "xsd:date"   → "date"
        "xs:decimal" → "decimal"
        None         → "complex"  (inline complexType)
        "MyCustomType" → "complex"  (unknown → treated as complex reference)
    """
    if xsd_type_name is None:
        return FIELD_TYPE_COMPLEX

    # Strip namespace prefix: "xs:string" → "string", "{...}string" → "string"
    local_name = xsd_type_name
    if "{" in local_name:
        local_name = local_name.split("}")[-1]
    elif ":" in local_name:
        local_name = local_name.split(":")[-1]

    return _XSD_TYPE_MAP.get(local_name, FIELD_TYPE_COMPLEX)


# ---------------------------------------------------------------------------
# FieldNode
# ---------------------------------------------------------------------------


@dataclass
class FieldNode:
    """A single node in the XSD field hierarchy.

    Attributes:
        name:      The element's ``name`` attribute from the XSD.
        path:      Dot-separated canonical path from the schema root, e.g.
                   ``cliente.endereco.cidade``.
        type:      Canonical type string — one of string/decimal/date/integer/
                   boolean/complex.
        required:  True when ``minOccurs`` is absent or ≥ 1.
        is_array:  True when ``maxOccurs`` is "unbounded" or > 1.
        children:  Ordered list of child FieldNodes (non-empty only for complex).
    """

    name: str
    path: str
    type: str
    required: bool
    is_array: bool
    children: list[FieldNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node (and all descendants) to a plain dict."""
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "required": self.required,
            "is_array": self.is_array,
            "children": [c.to_dict() for c in self.children],
        }


# ---------------------------------------------------------------------------
# FieldTree
# ---------------------------------------------------------------------------


@dataclass
class FieldTree:
    """The full field hierarchy extracted from an XSD schema.

    Attributes:
        root_nodes:  Top-level FieldNodes (direct children of xs:schema root
                     element, or multiple roots when the schema has no single
                     wrapper element).
        flat_paths:  Ordered list of every dot-separated path present in the
                     tree, enabling O(n) linear search.  Populated automatically
                     when ``build_flat_paths()`` is called (or use the class
                     method ``from_root_nodes``).
    """

    root_nodes: list[FieldNode]
    flat_paths: list[str] = field(default_factory=list)

    # --- Factory -----------------------------------------------------------

    @classmethod
    def from_root_nodes(cls, root_nodes: list[FieldNode]) -> FieldTree:
        """Create a FieldTree, computing flat_paths automatically."""
        tree = cls(root_nodes=root_nodes)
        tree.build_flat_paths()
        return tree

    # --- Traversal helpers -------------------------------------------------

    def build_flat_paths(self) -> None:
        """(Re)populate ``flat_paths`` via a depth-first traversal."""
        paths: list[str] = []
        stack = list(self.root_nodes)
        while stack:
            node = stack.pop(0)
            paths.append(node.path)
            stack = list(node.children) + stack  # pre-order
        self.flat_paths = paths

    def find_by_path(self, path: str) -> FieldNode | None:
        """Return the FieldNode matching *path*, or None if not found.

        Uses ``flat_paths`` for an early-exit index check before traversal.
        """
        if path not in self.flat_paths:
            return None
        return self._find_recursive(path, self.root_nodes)

    def _find_recursive(self, path: str, nodes: list[FieldNode]) -> FieldNode | None:
        for node in nodes:
            if node.path == path:
                return node
            result = self._find_recursive(path, node.children)
            if result is not None:
                return result
        return None

    # --- Serialisation -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full tree to a JSON-compatible dict."""
        return {
            "root_nodes": [n.to_dict() for n in self.root_nodes],
            "flat_paths": self.flat_paths,
        }
