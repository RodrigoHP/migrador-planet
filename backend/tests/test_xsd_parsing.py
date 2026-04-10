"""Tests for XSD Parser and FieldTree models (Story 5.6 AC: 1-9).

Run with:
    cd backend && python -m pytest tests/test_xsd_parsing.py -v
"""

from __future__ import annotations

from typing import Any

import pytest

from models.field_tree import FieldNode, FieldTree, map_xsd_type
from services.stages.xsd_parser import parse_xsd

# ---------------------------------------------------------------------------
# XSD fixtures
# ---------------------------------------------------------------------------

_XSD_SIMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="nome" type="xs:string"/>
        <xs:element name="cpf" type="xs:string"/>
        <xs:element name="data" type="xs:date"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_NESTED = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="cliente">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="nome" type="xs:string"/>
              <xs:element name="endereco">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="cidade" type="xs:string"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_ARRAY_UNBOUNDED = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="movimentos" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="data" type="xs:date"/>
              <xs:element name="valor" type="xs:decimal"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_ARRAY_INT = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" maxOccurs="5" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_OPTIONAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="obrigatorio" type="xs:string"/>
        <xs:element name="opcional" type="xs:string" minOccurs="0"/>
        <xs:element name="tambem_opcional" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_GLOBAL_COMPLEX_TYPE = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:complexType name="EnderecoType">
    <xs:sequence>
      <xs:element name="rua" type="xs:string"/>
      <xs:element name="cep" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>

  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="cliente">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="nome" type="xs:string"/>
              <xs:element name="endereco" type="EnderecoType"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_INVALID = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="nome" type="xs:string">
        <!-- tag not closed -->
</xs:schema>
"""


# ---------------------------------------------------------------------------
# AC 1 — test_simple_xsd: elementos flat (nome, cpf, data)
# ---------------------------------------------------------------------------


class TestSimpleXsd:
    """AC: 1 — Parse XSD simples com elementos flat."""

    def test_returns_field_tree(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        assert isinstance(tree, FieldTree)

    def test_three_root_nodes(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        assert len(tree.root_nodes) == 3

    def test_node_names(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        names = [n.name for n in tree.root_nodes]
        assert "nome" in names
        assert "cpf" in names
        assert "data" in names

    def test_node_types(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        by_name = {n.name: n for n in tree.root_nodes}
        assert by_name["nome"].type == "string"
        assert by_name["cpf"].type == "string"
        assert by_name["data"].type == "date"

    def test_flat_paths_populated(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        assert "nome" in tree.flat_paths
        assert "cpf" in tree.flat_paths
        assert "data" in tree.flat_paths

    def test_all_nodes_required_by_default(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        for node in tree.root_nodes:
            assert node.required is True

    def test_no_arrays_in_simple_xsd(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        for node in tree.root_nodes:
            assert node.is_array is False

    def test_to_dict_serializable(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        d = tree.to_dict()
        assert "root_nodes" in d
        assert "flat_paths" in d
        import json

        json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# AC 2 — test_nested_xsd: paths aninhados cliente.endereco.cidade
# ---------------------------------------------------------------------------


class TestNestedXsd:
    """AC: 2 — Suportar paths aninhados dot-separated."""

    def test_returns_field_tree(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert isinstance(tree, FieldTree)

    def test_cliente_root_node(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert any(n.name == "cliente" for n in tree.root_nodes)

    def test_cliente_nome_path(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert "cliente.nome" in tree.flat_paths

    def test_cliente_endereco_path(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert "cliente.endereco" in tree.flat_paths

    def test_cliente_endereco_cidade_path(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert "cliente.endereco.cidade" in tree.flat_paths

    def test_cliente_is_complex(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        cliente = tree.find_by_path("cliente")
        assert cliente is not None
        assert cliente.type == "complex"

    def test_cidade_is_string(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        cidade = tree.find_by_path("cliente.endereco.cidade")
        assert cidade is not None
        assert cidade.type == "string"

    def test_find_by_path_returns_correct_node(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        node = tree.find_by_path("cliente.endereco.cidade")
        assert node is not None
        assert node.name == "cidade"
        assert node.path == "cliente.endereco.cidade"

    def test_find_by_nonexistent_path_returns_none(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        assert tree.find_by_path("nao.existe") is None


# ---------------------------------------------------------------------------
# AC 3 — test_array_unbounded: maxOccurs="unbounded" → is_array = True
# ---------------------------------------------------------------------------


class TestArrayUnbounded:
    """AC: 3 — Detectar arrays via maxOccurs."""

    def test_unbounded_is_array(self) -> None:
        tree = parse_xsd(_XSD_ARRAY_UNBOUNDED)
        movimentos = tree.find_by_path("movimentos")
        assert movimentos is not None
        assert movimentos.is_array is True

    def test_unbounded_children_not_array(self) -> None:
        tree = parse_xsd(_XSD_ARRAY_UNBOUNDED)
        data = tree.find_by_path("movimentos.data")
        assert data is not None
        assert data.is_array is False

    def test_int_max_occurs_gt_1_is_array(self) -> None:
        tree = parse_xsd(_XSD_ARRAY_INT)
        item = tree.find_by_path("item")
        assert item is not None
        assert item.is_array is True

    def test_default_max_occurs_not_array(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        nome = tree.find_by_path("nome")
        assert nome is not None
        assert nome.is_array is False


# ---------------------------------------------------------------------------
# AC 4 — test_optional_field: minOccurs="0" → required = False
# ---------------------------------------------------------------------------


class TestOptionalField:
    """AC: 4 — Detectar campos opcionais via minOccurs."""

    def test_required_field_is_required(self) -> None:
        tree = parse_xsd(_XSD_OPTIONAL)
        obrigatorio = tree.find_by_path("obrigatorio")
        assert obrigatorio is not None
        assert obrigatorio.required is True

    def test_min_occurs_zero_is_optional(self) -> None:
        tree = parse_xsd(_XSD_OPTIONAL)
        opcional = tree.find_by_path("opcional")
        assert opcional is not None
        assert opcional.required is False

    def test_min_occurs_zero_unbounded_optional_and_array(self) -> None:
        tree = parse_xsd(_XSD_OPTIONAL)
        tambem = tree.find_by_path("tambem_opcional")
        assert tambem is not None
        assert tambem.required is False
        assert tambem.is_array is True


# ---------------------------------------------------------------------------
# AC 5 — FieldNode structure (tested via the other ACs, spot-check here)
# ---------------------------------------------------------------------------


class TestFieldNodeStructure:
    """AC: 5 — FieldNode output structure matches spec."""

    def test_field_node_has_all_attributes(self) -> None:
        node = FieldNode(
            name="test",
            path="root.test",
            type="string",
            required=True,
            is_array=False,
        )
        assert node.name == "test"
        assert node.path == "root.test"
        assert node.type == "string"
        assert node.required is True
        assert node.is_array is False
        assert node.children == []

    def test_field_node_to_dict(self) -> None:
        node = FieldNode(name="x", path="x", type="integer", required=False, is_array=True)
        d = node.to_dict()
        assert d == {
            "name": "x",
            "path": "x",
            "type": "integer",
            "required": False,
            "is_array": True,
            "children": [],
        }


# ---------------------------------------------------------------------------
# AC 6 — test_complex_type_reference: globally defined complex types
# ---------------------------------------------------------------------------


class TestComplexTypeReference:
    """AC: 6 — Resolver referências a complex types globais."""

    def test_endereco_resolved_as_complex(self) -> None:
        tree = parse_xsd(_XSD_GLOBAL_COMPLEX_TYPE)
        endereco = tree.find_by_path("cliente.endereco")
        assert endereco is not None
        assert endereco.type == "complex"

    def test_endereco_children_resolved(self) -> None:
        tree = parse_xsd(_XSD_GLOBAL_COMPLEX_TYPE)
        rua = tree.find_by_path("cliente.endereco.rua")
        cep = tree.find_by_path("cliente.endereco.cep")
        assert rua is not None, "cliente.endereco.rua deve existir"
        assert cep is not None, "cliente.endereco.cep deve existir"

    def test_rua_is_string(self) -> None:
        tree = parse_xsd(_XSD_GLOBAL_COMPLEX_TYPE)
        rua = tree.find_by_path("cliente.endereco.rua")
        assert rua is not None
        assert rua.type == "string"

    def test_flat_paths_include_deep_referenced_fields(self) -> None:
        tree = parse_xsd(_XSD_GLOBAL_COMPLEX_TYPE)
        assert "cliente.endereco.rua" in tree.flat_paths
        assert "cliente.endereco.cep" in tree.flat_paths


# ---------------------------------------------------------------------------
# AC 8 — test_invalid_xsd: XMLSyntaxError → ValueError
# ---------------------------------------------------------------------------


class TestInvalidXsd:
    """AC: 8 — XSD inválido gera ValueError com mensagem clara."""

    def test_invalid_xsd_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            parse_xsd(_XSD_INVALID)

    def test_error_message_mentions_parse(self) -> None:
        with pytest.raises(ValueError, match="Erro de parse XSD"):
            parse_xsd(_XSD_INVALID)

    def test_invalid_bytes_raises_value_error(self) -> None:
        bad_bytes = b"<xs:schema><unclosed"
        with pytest.raises(ValueError):
            parse_xsd(bad_bytes)

    def test_invalid_file_path_raises_file_not_found(self) -> None:
        from pathlib import Path

        with pytest.raises((FileNotFoundError, ValueError)):
            parse_xsd(Path("/tmp/nonexistent_xsd_file_xyz.xsd"))


# ---------------------------------------------------------------------------
# map_xsd_type unit tests (AC 1)
# ---------------------------------------------------------------------------


class TestMapXsdType:
    """Unit tests for the XSD type mapping helper."""

    def test_xs_string(self) -> None:
        assert map_xsd_type("xs:string") == "string"

    def test_xsd_string(self) -> None:
        assert map_xsd_type("xsd:string") == "string"

    def test_namespaced_string(self) -> None:
        assert map_xsd_type("{http://www.w3.org/2001/XMLSchema}string") == "string"

    def test_date(self) -> None:
        assert map_xsd_type("xs:date") == "date"

    def test_datetime(self) -> None:
        assert map_xsd_type("xs:dateTime") == "date"

    def test_decimal(self) -> None:
        assert map_xsd_type("xs:decimal") == "decimal"

    def test_integer(self) -> None:
        assert map_xsd_type("xs:integer") == "integer"

    def test_boolean(self) -> None:
        assert map_xsd_type("xs:boolean") == "boolean"

    def test_none_returns_complex(self) -> None:
        assert map_xsd_type(None) == "complex"

    def test_unknown_type_returns_complex(self) -> None:
        assert map_xsd_type("MyCustomComplexType") == "complex"


# ---------------------------------------------------------------------------
# FieldTree utility tests (AC 2, 5)
# ---------------------------------------------------------------------------


class TestFieldTreeUtilities:
    """Test FieldTree.find_by_path and to_dict utilities."""

    def _build_tree(self) -> FieldTree:
        child = FieldNode(name="cidade", path="cliente.cidade", type="string", required=True, is_array=False)
        root = FieldNode(
            name="cliente", path="cliente", type="complex", required=True, is_array=False, children=[child]
        )
        return FieldTree.from_root_nodes([root])

    def test_find_by_path_top_level(self) -> None:
        tree = self._build_tree()
        node = tree.find_by_path("cliente")
        assert node is not None
        assert node.name == "cliente"

    def test_find_by_path_nested(self) -> None:
        tree = self._build_tree()
        node = tree.find_by_path("cliente.cidade")
        assert node is not None
        assert node.name == "cidade"

    def test_find_by_path_missing(self) -> None:
        tree = self._build_tree()
        assert tree.find_by_path("nao.existe") is None

    def test_flat_paths_order(self) -> None:
        tree = self._build_tree()
        # pre-order: parent before child
        assert tree.flat_paths.index("cliente") < tree.flat_paths.index("cliente.cidade")

    def test_to_dict_structure(self) -> None:
        tree = self._build_tree()
        d = tree.to_dict()
        assert len(d["root_nodes"]) == 1
        assert d["root_nodes"][0]["name"] == "cliente"
        assert len(d["root_nodes"][0]["children"]) == 1
        assert "cliente" in d["flat_paths"]
        assert "cliente.cidade" in d["flat_paths"]


# ---------------------------------------------------------------------------
# Stage executor — auto-derive xsd_path from job_id
# ---------------------------------------------------------------------------


class TestXsdParserExecuteAutoDerive:
    """Tests for xsd_parser.execute auto-derive of xsd_path from job_id."""

    @pytest.mark.asyncio
    async def test_auto_derive_when_schema_exists(self, tmp_path) -> None:
        """execute() should auto-derive xsd_path from job_id when schema.xsd exists."""
        from services.stages.xsd_parser import execute

        job_dir = tmp_path / "job-abc"
        job_dir.mkdir()
        assets_dir = job_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "schema.xsd").write_text(_XSD_SIMPLE)

        context: dict[str, Any] = {"job_id": "job-abc", "tmp_base": str(tmp_path)}
        result = await execute(context)

        assert result["xsd_parsed"] is True
        field_tree: dict[str, Any] = context["field_tree"]
        assert field_tree is not None
        assert len(field_tree["flat_paths"]) > 0

    @pytest.mark.asyncio
    async def test_skips_when_no_schema_and_no_xsd_path(self, tmp_path) -> None:
        """execute() should skip gracefully when schema.xsd is not found."""
        from services.stages.xsd_parser import execute

        job_dir = tmp_path / "job-xyz"
        job_dir.mkdir()
        # No schema.xsd present

        context = {"job_id": "job-xyz", "tmp_base": str(tmp_path)}
        result = await execute(context)

        assert result["xsd_parsed"] is False
        assert context["field_tree"] is None

    @pytest.mark.asyncio
    async def test_explicit_xsd_path_takes_precedence(self, tmp_path) -> None:
        """Explicit context['xsd_path'] should be used instead of auto-derive."""
        from services.stages.xsd_parser import execute

        xsd_file = tmp_path / "custom.xsd"
        xsd_file.write_text(_XSD_SIMPLE)

        context = {"job_id": "job-other", "tmp_base": str(tmp_path), "xsd_path": str(xsd_file)}
        result = await execute(context)

        assert result["xsd_parsed"] is True
        assert context["field_tree"] is not None
