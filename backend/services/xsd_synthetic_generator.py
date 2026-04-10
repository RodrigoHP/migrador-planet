"""XSD Synthetic Generator — Story 38.5

Generates synthetic JSON data from XSD field descriptors (FieldTree).
Produces realistic values per type, including Brazilian document formats
(CPF, CNPJ, CEP, telefone) via field-name heuristics.

Usage:
    from services.xsd_synthetic_generator import XSDSyntheticGenerator
    from services.stages.xsd_parser import parse_xsd

    tree = parse_xsd(xsd_source)
    gen = XSDSyntheticGenerator()
    data = gen.generate(tree)
    # data is a dict mirroring the XSD structure with synthetic values

    # Or generate exemplo.js content:
    js_content = gen.generate_exemplo_js(tree)
"""

from __future__ import annotations

import json
import random
import re
from textwrap import dedent
from typing import Any

from models.field_tree import FieldNode, FieldTree

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ARRAY_MIN = 3
DEFAULT_ARRAY_MAX = 5
MAX_RECURSION_DEPTH = 5

# ---------------------------------------------------------------------------
# Brazilian value generators
# ---------------------------------------------------------------------------

_BR_FIRST_NAMES = [
    "João",
    "Maria",
    "Pedro",
    "Ana",
    "Carlos",
    "Fernanda",
    "Lucas",
    "Juliana",
    "Rafael",
    "Camila",
    "Bruno",
    "Beatriz",
    "Guilherme",
    "Larissa",
    "Marcos",
    "Patrícia",
    "Eduardo",
    "Vanessa",
    "Felipe",
    "Renata",
]

_BR_LAST_NAMES = [
    "Silva",
    "Santos",
    "Oliveira",
    "Souza",
    "Rodrigues",
    "Ferreira",
    "Alves",
    "Pereira",
    "Lima",
    "Gomes",
    "Costa",
    "Ribeiro",
    "Martins",
    "Carvalho",
    "Almeida",
    "Lopes",
    "Soares",
    "Fernandes",
    "Vieira",
    "Barbosa",
]

_BR_CITIES = [
    "São Paulo",
    "Rio de Janeiro",
    "Belo Horizonte",
    "Salvador",
    "Fortaleza",
    "Curitiba",
    "Manaus",
    "Recife",
    "Porto Alegre",
    "Belém",
]

_BR_STATES = ["SP", "RJ", "MG", "BA", "CE", "PR", "AM", "PE", "RS", "PA"]

_BR_STREETS = [
    "Rua das Flores",
    "Avenida Brasil",
    "Rua Sete de Setembro",
    "Avenida Paulista",
    "Rua Augusta",
    "Travessa das Acácias",
    "Rua Dom Pedro II",
    "Avenida Getúlio Vargas",
]

_LOREM_SENTENCES = [
    "Documento gerado automaticamente para testes.",
    "Texto de exemplo para validação do template.",
    "Informação sintética sem valor legal.",
    "Conteúdo fictício para demonstração.",
    "Dados de teste gerados pelo sistema.",
]


# ---------------------------------------------------------------------------
# CPF / CNPJ generators (valid check digits)
# ---------------------------------------------------------------------------


def _calc_cpf_digit(partial: list[int]) -> int:
    """Calculate a CPF check digit from a partial list of digits."""
    weight = len(partial) + 1
    total = sum(d * (weight - i) for i, d in enumerate(partial))
    rem = total % 11
    return 0 if rem < 2 else 11 - rem


def generate_cpf(rng: random.Random) -> str:
    """Generate a valid but fictitious CPF in XXX.XXX.XXX-XX format."""
    digits = [rng.randint(0, 9) for _ in range(9)]
    digits.append(_calc_cpf_digit(digits))
    digits.append(_calc_cpf_digit(digits))
    d = digits
    return f"{d[0]}{d[1]}{d[2]}.{d[3]}{d[4]}{d[5]}.{d[6]}{d[7]}{d[8]}-{d[9]}{d[10]}"


def _calc_cnpj_digit(partial: list[int], weights: list[int]) -> int:
    """Calculate a CNPJ check digit."""
    total = sum(d * w for d, w in zip(partial, weights))
    rem = total % 11
    return 0 if rem < 2 else 11 - rem


def generate_cnpj(rng: random.Random) -> str:
    """Generate a valid but fictitious CNPJ in XX.XXX.XXX/XXXX-XX format."""
    digits = [rng.randint(0, 9) for _ in range(8)]
    digits.extend([0, 0, 0, 1])  # branch
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    digits.append(_calc_cnpj_digit(digits, w1))
    digits.append(_calc_cnpj_digit(digits, w2))
    d = digits
    return f"{d[0]}{d[1]}.{d[2]}{d[3]}{d[4]}.{d[5]}{d[6]}{d[7]}/{d[8]}{d[9]}{d[10]}{d[11]}-{d[12]}{d[13]}"


def generate_cep(rng: random.Random) -> str:
    """Generate a fictitious CEP in XXXXX-XXX format."""
    return f"{rng.randint(10000, 99999):05d}-{rng.randint(100, 999):03d}"


def generate_phone(rng: random.Random) -> str:
    """Generate a fictitious phone in (XX) XXXXX-XXXX format."""
    ddd = rng.randint(11, 99)
    num1 = rng.randint(90000, 99999)
    num2 = rng.randint(1000, 9999)
    return f"({ddd:02d}) {num1}-{num2}"


def generate_name(rng: random.Random) -> str:
    """Generate a Brazilian-style full name."""
    return f"{rng.choice(_BR_FIRST_NAMES)} {rng.choice(_BR_LAST_NAMES)}"


def generate_date(rng: random.Random) -> str:
    """Generate an ISO date string (YYYY-MM-DD)."""
    year = rng.randint(2020, 2026)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"


def generate_datetime(rng: random.Random) -> str:
    """Generate an ISO datetime string."""
    return f"{generate_date(rng)}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00"


# ---------------------------------------------------------------------------
# Field name heuristics for BR types
# ---------------------------------------------------------------------------

_BR_PATTERNS: list[tuple] = [
    (re.compile(r"cpf", re.IGNORECASE), "cpf"),
    (re.compile(r"cnpj", re.IGNORECASE), "cnpj"),
    (re.compile(r"cep|cod.?postal|codigo.?postal", re.IGNORECASE), "cep"),
    (re.compile(r"telefone|fone|celular|phone|tel(?!e)", re.IGNORECASE), "phone"),
    (re.compile(r"inscricao.?estadual|ie\b", re.IGNORECASE), "ie"),
    (re.compile(r"nome|name|razao|cliente", re.IGNORECASE), "name"),
    (re.compile(r"cidade|city|municipio", re.IGNORECASE), "city"),
    (re.compile(r"estado|uf\b|state", re.IGNORECASE), "state"),
    (re.compile(r"endereco|logradouro|rua|address", re.IGNORECASE), "address"),
    (re.compile(r"email|e.?mail", re.IGNORECASE), "email"),
]


def _detect_br_type(field_name: str) -> str | None:
    """Detect a Brazilian semantic type from the field name."""
    for pattern, br_type in _BR_PATTERNS:
        if pattern.search(field_name):
            return br_type
    return None


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------


class XSDSyntheticGenerator:
    """Generates synthetic JSON data from XSD FieldTree structures.

    Args:
        seed: Random seed for reproducible output (None = non-deterministic).
        array_min: Minimum elements for array fields (default 3).
        array_max: Maximum elements for array fields (default 5).
    """

    def __init__(
        self,
        seed: int | None = None,
        array_min: int = DEFAULT_ARRAY_MIN,
        array_max: int = DEFAULT_ARRAY_MAX,
    ) -> None:
        self._rng = random.Random(seed)
        self._array_min = max(1, array_min)
        self._array_max = max(self._array_min, array_max)

    # --- Public API --------------------------------------------------------

    def generate(self, field_tree: FieldTree) -> dict[str, Any]:
        """Generate synthetic data matching the FieldTree structure.

        Args:
            field_tree: A FieldTree instance (from XSD parsing).

        Returns:
            A dict mirroring the XSD hierarchy with synthetic values.
        """
        if not field_tree or not field_tree.root_nodes:
            return {}
        return self._generate_from_nodes(field_tree.root_nodes, depth=0)

    def generate_from_dict(self, field_tree_dict: dict[str, Any]) -> dict[str, Any]:
        """Generate synthetic data from a serialized FieldTree dict.

        This is convenient when the FieldTree has already been serialized
        (e.g. from context["field_tree"]).

        Args:
            field_tree_dict: A dict with "root_nodes" key containing node dicts.

        Returns:
            A dict with synthetic values.
        """
        if not field_tree_dict:
            return {}
        root_nodes_raw = field_tree_dict.get("root_nodes", [])
        if not root_nodes_raw:
            return {}
        nodes = [self._dict_to_node(d) for d in root_nodes_raw]
        return self._generate_from_nodes(nodes, depth=0)

    def generate_exemplo_js(
        self,
        field_tree: FieldTree,
        *,
        var_name: str = "exemploData",
    ) -> str:
        """Generate the content of exemplo.js from a FieldTree.

        Args:
            field_tree: A FieldTree instance.
            var_name: JS variable name for the data object.

        Returns:
            A string with valid JS declaring the synthetic data object.
        """
        data = self.generate(field_tree)
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        return dedent(f"""\
            /* ============================================================
               exemplo.js — dados sintéticos gerados a partir do XSD
               Gerado automaticamente pelo XSDSyntheticGenerator
               ============================================================ */

            var {var_name} = {json_str};
        """)

    def generate_exemplo_js_from_dict(
        self,
        field_tree_dict: dict[str, Any],
        *,
        var_name: str = "exemploData",
    ) -> str:
        """Generate exemplo.js content from a serialized FieldTree dict."""
        data = self.generate_from_dict(field_tree_dict)
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        return dedent(f"""\
            /* ============================================================
               exemplo.js — dados sintéticos gerados a partir do XSD
               Gerado automaticamente pelo XSDSyntheticGenerator
               ============================================================ */

            var {var_name} = {json_str};
        """)

    # --- Internal ----------------------------------------------------------

    def _generate_from_nodes(self, nodes: list[FieldNode], depth: int) -> dict[str, Any]:
        """Recursively generate synthetic data for a list of FieldNodes."""
        result: dict[str, Any] = {}
        for node in nodes:
            if depth >= MAX_RECURSION_DEPTH:
                result[node.name] = self._generate_leaf_value(node)
                continue

            if node.is_array:
                count = self._rng.randint(self._array_min, self._array_max)
                if node.children:
                    result[node.name] = [self._generate_from_nodes(node.children, depth + 1) for _ in range(count)]
                else:
                    result[node.name] = [self._generate_leaf_value(node) for _ in range(count)]
            elif node.type == "complex" and node.children:
                result[node.name] = self._generate_from_nodes(node.children, depth + 1)
            else:
                result[node.name] = self._generate_leaf_value(node)

        return result

    def _generate_leaf_value(self, node: FieldNode) -> Any:
        """Generate a single value for a leaf node."""
        # Try BR heuristic first
        br_type = _detect_br_type(node.name)
        if br_type:
            return self._generate_br_value(br_type)

        # Fall back to XSD type
        return self._generate_by_type(node.type)

    def _generate_br_value(self, br_type: str) -> Any:
        """Generate a value for a detected Brazilian type."""
        generators = {
            "cpf": lambda: generate_cpf(self._rng),
            "cnpj": lambda: generate_cnpj(self._rng),
            "cep": lambda: generate_cep(self._rng),
            "phone": lambda: generate_phone(self._rng),
            "name": lambda: generate_name(self._rng),
            "city": lambda: self._rng.choice(_BR_CITIES),
            "state": lambda: self._rng.choice(_BR_STATES),
            "address": lambda: f"{self._rng.choice(_BR_STREETS)}, {self._rng.randint(1, 9999)}",
            "email": lambda: f"{self._rng.choice(_BR_FIRST_NAMES).lower()}@exemplo.com.br",
            "ie": lambda: "".join(str(self._rng.randint(0, 9)) for _ in range(12)),
        }
        gen = generators.get(br_type)
        return gen() if gen else self._generate_by_type("string")

    def _generate_by_type(self, field_type: str) -> Any:
        """Generate a value based on the canonical XSD type."""
        if field_type == "string":
            return self._rng.choice(_LOREM_SENTENCES)
        elif field_type == "integer":
            return self._rng.randint(1, 9999)
        elif field_type == "decimal":
            return round(self._rng.uniform(0.01, 99999.99), 2)
        elif field_type == "date":
            return generate_date(self._rng)
        elif field_type == "boolean":
            return self._rng.choice([True, False])
        else:
            # complex without children or unknown type
            return self._rng.choice(_LOREM_SENTENCES)

    @staticmethod
    def _dict_to_node(d: dict[str, Any]) -> FieldNode:
        """Convert a serialized node dict back to a FieldNode."""
        children = [XSDSyntheticGenerator._dict_to_node(c) for c in d.get("children", [])]
        return FieldNode(
            name=d.get("name", "unknown"),
            path=d.get("path", ""),
            type=d.get("type", "string"),
            required=d.get("required", True),
            is_array=d.get("is_array", False),
            children=children,
        )
