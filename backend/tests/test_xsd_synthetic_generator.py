"""Tests for XSD Synthetic Generator — Story 38.5

Run with:
    cd backend && python -m pytest tests/test_xsd_synthetic_generator.py -v
"""

from __future__ import annotations

import json
import re

from services.stages.xsd_parser import parse_xsd
from services.xsd_synthetic_generator import (
    XSDSyntheticGenerator,
    generate_cep,
    generate_cnpj,
    generate_cpf,
    generate_date,
    generate_datetime,
    generate_name,
    generate_phone,
)

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
        <xs:element name="valor" type="xs:decimal"/>
        <xs:element name="quantidade" type="xs:integer"/>
        <xs:element name="ativo" type="xs:boolean"/>
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
                    <xs:element name="cep" type="xs:string"/>
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

_XSD_ARRAY = """\
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

_XSD_BR_FIELDS = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="cadastro">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="cpf" type="xs:string"/>
        <xs:element name="cnpj" type="xs:string"/>
        <xs:element name="cep" type="xs:string"/>
        <xs:element name="telefone" type="xs:string"/>
        <xs:element name="celular" type="xs:string"/>
        <xs:element name="nome_cliente" type="xs:string"/>
        <xs:element name="email" type="xs:string"/>
        <xs:element name="cidade" type="xs:string"/>
        <xs:element name="estado" type="xs:string"/>
        <xs:element name="endereco" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

_XSD_EMPTY = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
</xs:schema>
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_gen(seed: int = 42) -> XSDSyntheticGenerator:
    return XSDSyntheticGenerator(seed=seed)


# ---------------------------------------------------------------------------
# AC1 — Service parses XSD and generates JSON example
# ---------------------------------------------------------------------------


class TestBasicGeneration:
    """AC1: xsd_synthetic_generator parseia XSD e gera JSON de exemplo."""

    def test_generates_dict_from_simple_xsd(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_all_fields_present(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert "nome" in data
        assert "cpf" in data
        assert "data" in data
        assert "valor" in data
        assert "quantidade" in data
        assert "ativo" in data

    def test_nested_structure(self) -> None:
        tree = parse_xsd(_XSD_NESTED)
        gen = _make_gen()
        data = gen.generate(tree)
        assert "cliente" in data
        assert isinstance(data["cliente"], dict)
        assert "nome" in data["cliente"]
        assert "endereco" in data["cliente"]
        assert "cidade" in data["cliente"]["endereco"]
        assert "cep" in data["cliente"]["endereco"]


# ---------------------------------------------------------------------------
# AC2 — Coherent values per type
# ---------------------------------------------------------------------------


class TestTypeCoherence:
    """AC2: Valores coerentes por tipo XSD."""

    def test_string_is_readable_text(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        # 'nome' is heuristic → name, but check it's a non-empty string
        assert isinstance(data["nome"], str)
        assert len(data["nome"]) > 0

    def test_date_is_valid_iso(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", data["data"])

    def test_decimal_is_number(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data["valor"], (int, float))

    def test_integer_is_int(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data["quantidade"], int)

    def test_boolean_is_bool(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data["ativo"], bool)


# ---------------------------------------------------------------------------
# AC3 — Brazilian types: CPF, CNPJ, CEP, telefone
# ---------------------------------------------------------------------------


class TestBrazilianTypes:
    """AC3: Tipos BR com formato real (válidos mas fictícios)."""

    def test_cpf_format(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", data["cpf"])

    def test_cnpj_format(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", data["cnpj"])

    def test_cep_format(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\d{5}-\d{3}$", data["cep"])

    def test_telefone_format(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\(\d{2}\) \d{5}-\d{4}$", data["telefone"])

    def test_celular_also_phone(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert re.match(r"^\(\d{2}\) \d{5}-\d{4}$", data["celular"])

    def test_nome_cliente_is_name(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        # Should be a name with first and last
        parts = data["nome_cliente"].split()
        assert len(parts) >= 2

    def test_email_format(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert "@" in data["email"]

    def test_cidade_is_br_city(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data["cidade"], str)
        assert len(data["cidade"]) > 2

    def test_estado_is_uf(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert len(data["estado"]) == 2

    def test_endereco_is_address(self) -> None:
        tree = parse_xsd(_XSD_BR_FIELDS)
        gen = _make_gen()
        data = gen.generate(tree)
        assert isinstance(data["endereco"], str)
        assert len(data["endereco"]) > 5


# ---------------------------------------------------------------------------
# AC3b — CPF/CNPJ check digit validation
# ---------------------------------------------------------------------------


class TestCheckDigitValidation:
    """Verify CPF/CNPJ check digits are valid."""

    @staticmethod
    def _validate_cpf(cpf_str: str) -> bool:
        digits = [int(c) for c in cpf_str if c.isdigit()]
        if len(digits) != 11:
            return False
        # First check digit
        total = sum(d * (10 - i) for i, d in enumerate(digits[:9]))
        rem = total % 11
        d1 = 0 if rem < 2 else 11 - rem
        if digits[9] != d1:
            return False
        # Second check digit
        total = sum(d * (11 - i) for i, d in enumerate(digits[:10]))
        rem = total % 11
        d2 = 0 if rem < 2 else 11 - rem
        return digits[10] == d2

    @staticmethod
    def _validate_cnpj(cnpj_str: str) -> bool:
        digits = [int(c) for c in cnpj_str if c.isdigit()]
        if len(digits) != 14:
            return False
        w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(d * w for d, w in zip(digits[:12], w1))
        rem = total % 11
        d1 = 0 if rem < 2 else 11 - rem
        if digits[12] != d1:
            return False
        w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(d * w for d, w in zip(digits[:13], w2))
        rem = total % 11
        d2 = 0 if rem < 2 else 11 - rem
        return digits[13] == d2

    def test_generated_cpf_has_valid_digits(self) -> None:
        import random as _r

        rng = _r.Random(42)
        for _ in range(10):
            cpf = generate_cpf(rng)
            assert self._validate_cpf(cpf), f"Invalid CPF: {cpf}"

    def test_generated_cnpj_has_valid_digits(self) -> None:
        import random as _r

        rng = _r.Random(42)
        for _ in range(10):
            cnpj = generate_cnpj(rng)
            assert self._validate_cnpj(cnpj), f"Invalid CNPJ: {cnpj}"


# ---------------------------------------------------------------------------
# AC4 — Arrays generate 3-5 elements
# ---------------------------------------------------------------------------


class TestArrayGeneration:
    """AC4: Arrays geram 3-5 elementos por padrão."""

    def test_array_has_3_to_5_elements(self) -> None:
        tree = parse_xsd(_XSD_ARRAY)
        gen = _make_gen()
        data = gen.generate(tree)
        assert "movimentos" in data
        assert isinstance(data["movimentos"], list)
        assert 3 <= len(data["movimentos"]) <= 5

    def test_array_elements_have_children(self) -> None:
        tree = parse_xsd(_XSD_ARRAY)
        gen = _make_gen()
        data = gen.generate(tree)
        for item in data["movimentos"]:
            assert "data" in item
            assert "valor" in item

    def test_custom_array_bounds(self) -> None:
        tree = parse_xsd(_XSD_ARRAY)
        gen = XSDSyntheticGenerator(seed=42, array_min=1, array_max=2)
        data = gen.generate(tree)
        assert 1 <= len(data["movimentos"]) <= 2


# ---------------------------------------------------------------------------
# AC5 — Result available as exemplo.js
# ---------------------------------------------------------------------------


class TestExemploJs:
    """AC5: Resultado disponível como exemplo.js."""

    def test_generates_valid_js_string(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        js = gen.generate_exemplo_js(tree)
        assert isinstance(js, str)
        assert "var exemploData" in js

    def test_js_contains_valid_json_data(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        js = gen.generate_exemplo_js(tree)
        # Extract the JSON part
        match = re.search(r"var exemploData = ({.*?});", js, re.DOTALL)
        assert match is not None
        data = json.loads(match.group(1))
        assert "nome" in data

    def test_custom_var_name(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        js = gen.generate_exemplo_js(tree, var_name="myData")
        assert "var myData" in js

    def test_generate_from_dict(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        tree_dict = tree.to_dict()
        gen = _make_gen()
        js = gen.generate_exemplo_js_from_dict(tree_dict)
        assert "var exemploData" in js
        match = re.search(r"var exemploData = ({.*?});", js, re.DOTALL)
        assert match is not None


# ---------------------------------------------------------------------------
# AC6 — testDataStore can use generated data
# ---------------------------------------------------------------------------


class TestStoreCompatibility:
    """AC6: testDataStore pode usar dados gerados automaticamente."""

    def test_output_is_json_serializable(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen = _make_gen()
        data = gen.generate(tree)
        # Must be JSON-serializable (Dataset.fields expects Record<string, unknown>)
        serialized = json.dumps(data, ensure_ascii=False)
        assert len(serialized) > 0

    def test_generate_from_dict_matches_generate(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        tree_dict = tree.to_dict()
        gen1 = XSDSyntheticGenerator(seed=42)
        gen2 = XSDSyntheticGenerator(seed=42)
        data1 = gen1.generate(tree)
        data2 = gen2.generate_from_dict(tree_dict)
        assert data1 == data2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Graceful handling of empty/invalid input."""

    def test_empty_xsd_returns_empty_dict(self) -> None:
        tree = parse_xsd(_XSD_EMPTY)
        gen = _make_gen()
        data = gen.generate(tree)
        assert data == {}

    def test_none_field_tree_returns_empty_dict(self) -> None:
        gen = _make_gen()
        data = gen.generate_from_dict(None)  # type: ignore[arg-type]
        assert data == {}

    def test_empty_dict_returns_empty(self) -> None:
        gen = _make_gen()
        data = gen.generate_from_dict({})
        assert data == {}

    def test_seed_produces_deterministic_output(self) -> None:
        tree = parse_xsd(_XSD_SIMPLE)
        gen1 = XSDSyntheticGenerator(seed=123)
        gen2 = XSDSyntheticGenerator(seed=123)
        assert gen1.generate(tree) == gen2.generate(tree)


# ---------------------------------------------------------------------------
# Standalone helper function tests
# ---------------------------------------------------------------------------


class TestStandaloneGenerators:
    """Test individual generator functions."""

    def test_generate_cep_format(self) -> None:
        import random as _r

        rng = _r.Random(42)
        cep = generate_cep(rng)
        assert re.match(r"^\d{5}-\d{3}$", cep)

    def test_generate_phone_format(self) -> None:
        import random as _r

        rng = _r.Random(42)
        phone = generate_phone(rng)
        assert re.match(r"^\(\d{2}\) \d{5}-\d{4}$", phone)

    def test_generate_name_has_two_parts(self) -> None:
        import random as _r

        rng = _r.Random(42)
        name = generate_name(rng)
        assert len(name.split()) >= 2

    def test_generate_date_is_iso(self) -> None:
        import random as _r

        rng = _r.Random(42)
        date = generate_date(rng)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", date)

    def test_generate_datetime_has_time(self) -> None:
        import random as _r

        rng = _r.Random(42)
        dt = generate_datetime(rng)
        assert "T" in dt
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", dt)
