"""Integration Tests — Stage 1 + Stage 2 end-to-end + Performance Benchmark.

Story 13.6 — Validates that Stage 1 (Layout Clustering) output feeds correctly
into Stage 2 (Deep Extraction), contracts 3.1 and 3.2 are valid, edge cases
are handled, and performance meets the 16s target for 100 pages.

All PDFs are generated programmatically with PyMuPDF (no external files).
Storage uses LocalStorageGateway with tmp_path.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import fitz  # PyMuPDF
import pytest

# ---------------------------------------------------------------------------
# Ensure backend is on sys.path so "services.*" imports resolve
# ---------------------------------------------------------------------------
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.storage.local_gateway import LocalStorageGateway
from tests.schemas import validate_contract

pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage module loaders (lazy to avoid import-time side effects)
# ---------------------------------------------------------------------------


def _get_stage1():
    import services.stages.stage1_layout_clustering as mod

    return mod


def _get_stage2():
    import services.stages.stage2_deep_extraction as mod

    return mod


# ---------------------------------------------------------------------------
# No-op progress emitter
# ---------------------------------------------------------------------------


async def _noop_emit(event: dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


# ---------------------------------------------------------------------------
# PDF Generators (all programmatic with PyMuPDF)
# ---------------------------------------------------------------------------


def _create_simple_boleto_pdf(path: str, num_pages: int = 5) -> None:
    """5 identical pages — boleto-like layout."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        # Header
        page.insert_text((50, 40), "Banco Nacional S.A.", fontsize=14)
        page.insert_text((400, 40), "BOLETO", fontsize=12)
        # Body — consistent layout across pages
        page.insert_text((50, 120), f"Sacado: Cliente {i + 1}", fontsize=10)
        page.insert_text((50, 150), f"CPF: 123.456.789-{10 + i}", fontsize=10)
        page.insert_text((50, 200), f"Vencimento: {10 + i}/04/2026", fontsize=10)
        page.insert_text((50, 250), f"Valor: R$ {1000 + i * 100},00", fontsize=10)
        page.insert_text((50, 300), "Referente a servicos prestados conforme contrato vigente", fontsize=10)
        page.insert_text((50, 350), f"Nosso Numero: {900000 + i}", fontsize=10)
        # Footer
        page.insert_text((50, 800), f"Pagina {i + 1} de {num_pages}", fontsize=8)
    doc.save(path)
    doc.close()


def _create_two_layout_pdf(path: str) -> None:
    """PDF with 2 different layouts: cover page + report pages."""
    doc = fitz.open()

    # Layout A: cover page (1 page — centered, large text)
    page = doc.new_page(width=595, height=842)
    page.insert_text((200, 300), "RELATORIO ANUAL", fontsize=24)
    page.insert_text((220, 360), "Exercicio 2025", fontsize=16)
    page.insert_text((180, 420), "Empresa Exemplo Ltda", fontsize=14)

    # Layout B: report pages (4 pages — left-aligned, multi-line body)
    for i in range(4):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 40), "Empresa Exemplo Ltda", fontsize=10)
        page.insert_text((50, 120), "Secao de Analise Financeira", fontsize=12)
        page.insert_text((50, 160), f"Periodo: {i + 1}o Trimestre 2025", fontsize=10)
        page.insert_text((50, 200), f"Receita: R$ {50000 + i * 10000},00", fontsize=10)
        page.insert_text((50, 240), f"Despesas: R$ {30000 + i * 5000},00", fontsize=10)
        page.insert_text((50, 280), "Observacoes sobre o desempenho do periodo corrente", fontsize=10)
        page.insert_text((50, 320), "Dados consolidados conforme auditoria externa", fontsize=10)
        page.insert_text((50, 800), f"Pagina {i + 2} de 5", fontsize=8)

    doc.save(path)
    doc.close()


def _create_template_pdf(path: str, num_pages: int = 5, variation: int = 0) -> None:
    """Create a PDF of a specific template with dynamic content variation."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        # Consistent structure
        page.insert_text((50, 40), "Companhia ABC", fontsize=12)
        page.insert_text((50, 120), "Extrato de Conta Corrente", fontsize=14)
        page.insert_text((50, 170), f"Titular: Pessoa {variation}", fontsize=10)
        page.insert_text((50, 200), f"Agencia: 0{variation + 1}23", fontsize=10)
        page.insert_text((50, 230), f"Data: {10 + variation}/03/2026", fontsize=10)
        page.insert_text((50, 280), f"Saldo: R$ {5000 + variation * 500 + i * 100},00", fontsize=10)
        page.insert_text((50, 320), "Movimentacao referente ao periodo anterior", fontsize=10)
        page.insert_text((50, 800), f"Pag {i + 1}/{num_pages}", fontsize=8)
    doc.save(path)
    doc.close()


def _create_incompatible_pdf(path: str, num_pages: int = 3) -> None:
    """PDF with completely different layout (landscape, centered)."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=842, height=595)  # Landscape
        page.insert_text((300, 100), "CERTIFICADO", fontsize=24)
        page.insert_text((200, 200), f"Certificamos que Pessoa {i}", fontsize=16)
        page.insert_text((200, 280), "concluiu o programa em 01/01/2026", fontsize=12)
        page.insert_text((350, 400), "Assinatura: ___________", fontsize=10)
    doc.save(path)
    doc.close()


def _create_blank_page_pdf(path: str) -> None:
    """PDF with 3 text pages + 1 blank page in the middle."""
    doc = fitz.open()
    # Page 0: text
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "Documento com pagina em branco", fontsize=12)
    page.insert_text((50, 200), "Conteudo da primeira pagina do documento", fontsize=10)
    page.insert_text((50, 250), "Valor: R$ 1.000,00", fontsize=10)
    # Page 1: blank
    doc.new_page(width=595, height=842)
    # Page 2: text (same layout as page 0)
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "Documento com pagina em branco", fontsize=12)
    page.insert_text((50, 200), "Conteudo da terceira pagina do documento", fontsize=10)
    page.insert_text((50, 250), "Valor: R$ 2.000,00", fontsize=10)
    doc.save(path)
    doc.close()


def _create_rotated_pdf(path: str) -> None:
    """PDF with a 90-degree rotated page."""
    doc = fitz.open()
    # Page 0: normal
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "Pagina normal orientacao retrato", fontsize=12)
    page.insert_text((50, 200), "Data: 15/03/2026", fontsize=10)
    page.insert_text((50, 250), "Valor: R$ 3.500,00", fontsize=10)
    # Page 1: rotated 90 degrees
    page = doc.new_page(width=595, height=842)
    page.set_rotation(90)
    page.insert_text((50, 120), "Pagina rotacionada noventa graus", fontsize=12)
    page.insert_text((50, 200), "Data: 16/03/2026", fontsize=10)
    page.insert_text((50, 250), "Valor: R$ 4.200,00", fontsize=10)
    doc.save(path)
    doc.close()


def _create_table_no_borders_pdf(path: str) -> None:
    """PDF with a table that has NO ruling lines (borderless table)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 40), "Relatorio de Vendas", fontsize=14)
    # Simulate a borderless table with aligned text columns
    # Header row
    page.insert_text((50, 120), "Produto", fontsize=10)
    page.insert_text((200, 120), "Quantidade", fontsize=10)
    page.insert_text((350, 120), "Preco", fontsize=10)
    # Data rows
    page.insert_text((50, 150), "Widget A", fontsize=10)
    page.insert_text((200, 150), "100", fontsize=10)
    page.insert_text((350, 150), "R$ 25,00", fontsize=10)
    page.insert_text((50, 180), "Widget B", fontsize=10)
    page.insert_text((200, 180), "50", fontsize=10)
    page.insert_text((350, 180), "R$ 45,00", fontsize=10)
    page.insert_text((50, 210), "Widget C", fontsize=10)
    page.insert_text((200, 210), "75", fontsize=10)
    page.insert_text((350, 210), "R$ 30,00", fontsize=10)
    page.insert_text((50, 240), "Widget D", fontsize=10)
    page.insert_text((200, 240), "200", fontsize=10)
    page.insert_text((350, 240), "R$ 15,00", fontsize=10)
    doc.save(path)
    doc.close()


def _create_image_no_bbox_pdf(path: str) -> None:
    """PDF with an embedded image that may lack a valid bbox."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "Documento com imagem", fontsize=12)
    page.insert_text((50, 200), "Logo da empresa abaixo", fontsize=10)
    # Create a small in-memory PNG (20x20 red square)
    import struct
    import zlib

    width_px, height_px = 20, 20
    raw_data = b""
    for _ in range(height_px):
        raw_data += b"\x00"  # filter byte
        for _ in range(width_px):
            raw_data += b"\xff\x00\x00"  # RGB red

    def _make_png(w: int, h: int, data: bytes) -> bytes:
        def _chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
            c = chunk_type + chunk_data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(chunk_data)) + c + crc

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
        return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(data)) + _chunk(b"IEND", b"")

    png_bytes = _make_png(width_px, height_px, raw_data)
    # Insert image into page
    page.insert_image(fitz.Rect(100, 300, 200, 400), stream=png_bytes)
    doc.save(path)
    doc.close()


def _create_100_page_pdf(path: str) -> None:
    """Generate a 100-page PDF for performance benchmark."""
    doc = fitz.open()
    for i in range(100):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 40), "Banco Nacional S.A.", fontsize=14)
        page.insert_text((50, 120), f"Cliente: Pessoa {i}", fontsize=10)
        page.insert_text((50, 150), f"CPF: 123.456.789-{i % 100:02d}", fontsize=10)
        page.insert_text((50, 200), f"Data: {(i % 28) + 1:02d}/04/2026", fontsize=10)
        page.insert_text((50, 250), f"Valor: R$ {1000 + i * 50},00", fontsize=10)
        page.insert_text((50, 300), "Descricao padrao de transacao bancaria realizada", fontsize=10)
        page.insert_text((50, 350), f"Ref: {100000 + i}", fontsize=10)
        page.insert_text((50, 800), f"Pag {i + 1}/100", fontsize=8)
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def _make_context(
    pdf_documents: list[dict[str, str]],
    storage: Any = None,
    job_id: str = "test-integration",
) -> dict[str, Any]:
    """Build a minimal pipeline context for Stage 1 + Stage 2."""
    return {
        "_storage": storage,
        "_current_stage": 0,
        "_current_stage_name": "",
        "pdf_documents": pdf_documents,
        "xsd_path": "",
        "job_id": job_id,
        "_job": {"job_id": job_id, "status": "running", "config": {}},
    }


# ═══════════════════════════════════════════════════════════════════════════
# Task 3: Integration Tests (AC: 1-3, 7)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_stage1_to_stage2_single_pdf(tmp_path):
    """AC-1: 1 PDF -> Stage 1 (clusters) -> Stage 2 (extraction) -> contracts 3.1 and 3.2 valid."""
    stage1 = _get_stage1()
    stage2 = _get_stage2()

    pdf_path = str(tmp_path / "boleto.pdf")
    _create_simple_boleto_pdf(pdf_path, num_pages=5)

    storage = LocalStorageGateway(tmp_base=tmp_path / "storage")
    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "boleto.pdf"}]
    context = _make_context(pdf_docs, storage=storage)

    # Run Stage 1
    context = await stage1.run_stage1(context, _noop_emit)

    clusters = context["clusters"]
    assert len(clusters) >= 1, "Stage 1 must produce at least 1 cluster"

    # Validate contract 3.1
    validate_contract(clusters, "contract_3_1")

    # Run Stage 2
    context = await stage2.run_stage2(context, _noop_emit)

    enriched = context["enriched_documents"]
    assert len(enriched) >= 1, "Stage 2 must produce at least 1 enriched document"

    # Validate contract 3.2
    validate_contract(enriched, "contract_3_2")

    # Verify representative pages have text_blocks
    for doc_data in enriched:
        for page in doc_data["pages"]:
            if page["is_representative"]:
                assert len(page["text_blocks"]) > 0, f"Representative page {page['page_index']} must have text_blocks"
                assert page["width"] > 0
                assert page["height"] > 0


@pytest.mark.asyncio
async def test_stage1_to_stage2_multi_pdf(tmp_path):
    """AC-2: 3 PDFs same template -> single pool -> pdf_id preserved."""
    stage1 = _get_stage1()
    stage2 = _get_stage2()

    pdf_docs = []
    for i in range(3):
        pdf_path = str(tmp_path / f"template_{i}.pdf")
        _create_template_pdf(pdf_path, num_pages=5, variation=i)
        pdf_docs.append({"id": f"pdf-{i}", "path": pdf_path, "name": f"template_{i}.pdf"})

    storage = LocalStorageGateway(tmp_base=tmp_path / "storage")
    context = _make_context(pdf_docs, storage=storage)

    # Run Stage 1
    context = await stage1.run_stage1(context, _noop_emit)
    clusters = context["clusters"]
    validate_contract(clusters, "contract_3_1")

    # Verify pdf_id is preserved in cluster pages
    all_pdf_ids_in_clusters = set()
    for cluster in clusters:
        for page in cluster["pages"]:
            all_pdf_ids_in_clusters.add(page["pdf_id"])

    expected_ids = {"pdf-0", "pdf-1", "pdf-2"}
    assert expected_ids.issubset(all_pdf_ids_in_clusters), (
        f"All 3 pdf_ids must appear in clusters. Found: {all_pdf_ids_in_clusters}"
    )

    # Run Stage 2
    context = await stage2.run_stage2(context, _noop_emit)
    enriched = context["enriched_documents"]
    validate_contract(enriched, "contract_3_2")

    # Verify pdf_id preserved in enriched documents
    enriched_pdf_ids = {doc["pdf_id"] for doc in enriched}
    assert expected_ids.issubset(enriched_pdf_ids), (
        f"All 3 pdf_ids must appear in enriched_documents. Found: {enriched_pdf_ids}"
    )


@pytest.mark.asyncio
async def test_homogeneity_check_detects_mismatch(tmp_path):
    """AC-3: PDF of different template -> detected by homogeneity check (shared_ratio < 0.20)."""
    stage1 = _get_stage1()

    # 2 PDFs of same template
    pdf_docs = []
    for i in range(2):
        pdf_path = str(tmp_path / f"same_{i}.pdf")
        _create_template_pdf(pdf_path, num_pages=5, variation=i)
        pdf_docs.append({"id": f"pdf-{i}", "path": pdf_path, "name": f"same_{i}.pdf"})

    # 1 incompatible PDF
    incompat_path = str(tmp_path / "incompatible.pdf")
    _create_incompatible_pdf(incompat_path)
    pdf_docs.append({"id": "pdf-incompat", "path": incompat_path, "name": "incompatible.pdf"})

    context = _make_context(pdf_docs)

    # Run Stage 1 — patch handle_service_failure to avoid 300s operator-wait
    with patch(
        "services.pipeline_orchestrator_v2.handle_service_failure",
        new_callable=AsyncMock,
    ) as _mock_hsf:
        _mock_hsf.return_value = "fallback"
        context = await stage1.run_stage1(context, _noop_emit)
    clusters = context["clusters"]
    validate_contract(clusters, "contract_3_1")

    # The incompatible PDF should be in its own cluster(s) not shared with others.
    # Check that incompatible pages are isolated.
    incompat_clusters = []
    shared_clusters = []
    for cluster in clusters:
        if cluster["cluster_id"].startswith("_"):
            continue
        page_pdfs = {p["pdf_id"] for p in cluster["pages"]}
        if "pdf-incompat" in page_pdfs:
            if page_pdfs == {"pdf-incompat"}:
                incompat_clusters.append(cluster)
            else:
                shared_clusters.append(cluster)

    # The incompatible PDF should NOT share clusters with the template PDFs
    # (or if it does, shared_ratio should be very low)
    assert len(shared_clusters) == 0, (
        f"Incompatible PDF should not share clusters with template PDFs. Shared clusters: {shared_clusters}"
    )


@pytest.mark.asyncio
async def test_raw_text_blocks_preserved(tmp_path):
    """AC-7: _raw_text_blocks preserved with real text (pre-abstraction) accessible for Stage 3."""
    stage1 = _get_stage1()

    pdf_path = str(tmp_path / "boleto.pdf")
    _create_simple_boleto_pdf(pdf_path, num_pages=3)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "boleto.pdf"}]
    context = _make_context(pdf_docs)

    context = await stage1.run_stage1(context, _noop_emit)

    raw_blocks = context.get("_raw_text_blocks", {})
    assert len(raw_blocks) > 0, "_raw_text_blocks must not be empty"

    # Verify structure: keys are "pdf_id:page_index"
    for key, blocks in raw_blocks.items():
        parts = key.split(":")
        assert len(parts) == 2, f"Key must be 'pdf_id:page_index', got '{key}'"
        assert parts[0] == "pdf-0"
        assert int(parts[1]) >= 0

        # Verify blocks contain real text (not abstracted)
        for block in blocks:
            assert "text" in block, "Block must have 'text' field"
            assert "bbox_norm" in block, "Block must have 'bbox_norm' field"
            assert len(block["bbox_norm"]) == 4, "bbox_norm must have 4 elements"
            assert block["type"] == 0, "Only type 0 (text) blocks should be preserved"

    # Verify real text content is preserved (not abstracted like DATE/NUMBER/TEXT_S)
    all_texts = []
    for blocks in raw_blocks.values():
        for block in blocks:
            all_texts.append(block["text"])

    # Should contain real text like "Banco Nacional" or CPF patterns
    joined = " ".join(all_texts)
    assert any(term in joined for term in ["Banco Nacional", "Cliente", "Sacado", "CPF", "123.456"]), (
        f"Raw text blocks should contain real text, not abstractions. Got: {joined[:500]}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Task 4: Edge Cases (AC: 6)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_blank_page_classified(tmp_path):
    """AC-6: Blank page -> page_type: 'blank' in a special cluster."""
    stage1 = _get_stage1()

    pdf_path = str(tmp_path / "with_blank.pdf")
    _create_blank_page_pdf(pdf_path)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "with_blank.pdf"}]
    context = _make_context(pdf_docs)

    context = await stage1.run_stage1(context, _noop_emit)
    clusters = context["clusters"]
    validate_contract(clusters, "contract_3_1")

    # Find the _blank cluster
    blank_clusters = [c for c in clusters if c["cluster_id"] == "_blank"]
    assert len(blank_clusters) == 1, "Should have exactly 1 _blank cluster"

    blank_cluster = blank_clusters[0]
    assert blank_cluster["page_count"] >= 1, "Blank cluster must have at least 1 page"

    # Verify blank page is page index 1 (middle page)
    blank_page_indices = [p["page_index"] for p in blank_cluster["pages"]]
    assert 1 in blank_page_indices, f"Page 1 (blank) should be in _blank cluster. Found indices: {blank_page_indices}"


@pytest.mark.asyncio
async def test_rotated_pdf_normalized(tmp_path):
    """AC-6: Rotated PDF -> normalized coordinates are within [0,1]."""
    stage1 = _get_stage1()

    pdf_path = str(tmp_path / "rotated.pdf")
    _create_rotated_pdf(pdf_path)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "rotated.pdf"}]
    context = _make_context(pdf_docs)

    context = await stage1.run_stage1(context, _noop_emit)

    raw_blocks = context.get("_raw_text_blocks", {})
    assert len(raw_blocks) > 0

    # Check that all normalized coordinates are in [0, 1]
    for key, blocks in raw_blocks.items():
        for block in blocks:
            bbox = block["bbox_norm"]
            for coord in bbox:
                assert 0.0 <= coord <= 1.0, f"Normalized coord out of range in page {key}: {bbox}"


@pytest.mark.asyncio
async def test_table_without_ruling_lines(tmp_path):
    """AC-6: Table without borders -> detection_method = 'clustering'."""
    stage1 = _get_stage1()
    stage2 = _get_stage2()

    pdf_path = str(tmp_path / "table_no_borders.pdf")
    _create_table_no_borders_pdf(pdf_path)

    storage = LocalStorageGateway(tmp_base=tmp_path / "storage")
    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "table_no_borders.pdf"}]
    context = _make_context(pdf_docs, storage=storage)

    # Run Stage 1 + Stage 2
    context = await stage1.run_stage1(context, _noop_emit)
    context = await stage2.run_stage2(context, _noop_emit)

    enriched = context["enriched_documents"]
    validate_contract(enriched, "contract_3_2")

    # Check tables on representative pages
    for doc_data in enriched:
        for page in doc_data["pages"]:
            if page["is_representative"] and page["tables"]:
                for table in page["tables"]:
                    if not table["has_ruling_lines"]:
                        assert table["detection_method"] == "clustering", (
                            f"Table without ruling lines should use detection_method='clustering', "
                            f"got '{table['detection_method']}'"
                        )


@pytest.mark.asyncio
async def test_image_invalid_bbox(tmp_path):
    """AC-6: Image without valid bbox -> bbox_valid: False."""
    stage1 = _get_stage1()
    stage2 = _get_stage2()

    pdf_path = str(tmp_path / "image_doc.pdf")
    _create_image_no_bbox_pdf(pdf_path)

    storage = LocalStorageGateway(tmp_base=tmp_path / "storage")
    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "image_doc.pdf"}]
    context = _make_context(pdf_docs, storage=storage)

    # Run Stage 1 + Stage 2
    context = await stage1.run_stage1(context, _noop_emit)
    context = await stage2.run_stage2(context, _noop_emit)

    enriched = context["enriched_documents"]
    validate_contract(enriched, "contract_3_2")

    # Find images on representative pages
    all_images = []
    for doc_data in enriched:
        for page in doc_data["pages"]:
            if page["is_representative"]:
                all_images.extend(page["images"])

    # If images found, verify bbox_valid is a boolean
    for img in all_images:
        assert isinstance(img["bbox_valid"], bool), "bbox_valid must be a boolean"
        # Images with zero bbox should be marked invalid
        if img["bbox"] == [0.0, 0.0, 0.0, 0.0]:
            assert img["bbox_valid"] is False, "Image with zero bbox should have bbox_valid=False"


# ═══════════════════════════════════════════════════════════════════════════
# Task 5: Performance Benchmark (AC: 4)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_performance_100_pages(tmp_path):
    """AC-4: 100 pages -> Stage 1 + Stage 2 combined < 16s."""
    stage1 = _get_stage1()
    stage2 = _get_stage2()

    pdf_path = str(tmp_path / "perf_100.pdf")
    _create_100_page_pdf(pdf_path)

    storage = LocalStorageGateway(tmp_base=tmp_path / "storage")
    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "perf_100.pdf"}]
    context = _make_context(pdf_docs, storage=storage)

    # Stage 1 benchmark
    t0 = time.perf_counter()
    context = await stage1.run_stage1(context, _noop_emit)
    t1 = time.perf_counter()
    stage1_time = t1 - t0

    clusters = context["clusters"]
    validate_contract(clusters, "contract_3_1")

    # Stage 2 benchmark
    t2 = time.perf_counter()
    context = await stage2.run_stage2(context, _noop_emit)
    t3 = time.perf_counter()
    stage2_time = t3 - t2

    enriched = context["enriched_documents"]
    validate_contract(enriched, "contract_3_2")

    total_time = stage1_time + stage2_time

    # Log breakdown
    logger.info("=" * 60)
    logger.info("PERFORMANCE BENCHMARK — 100 pages")
    logger.info("-" * 60)
    logger.info("Stage 1 (Layout Clustering): %.2fs", stage1_time)
    logger.info("Stage 2 (Deep Extraction):   %.2fs", stage2_time)
    logger.info("TOTAL:                       %.2fs", total_time)
    logger.info("Target:                      < 16.0s")
    logger.info("=" * 60)

    # Print to stdout for pytest -s visibility
    print(f"\n{'=' * 60}")
    print("PERFORMANCE BENCHMARK - 100 pages")
    print(f"{'-' * 60}")
    print(f"Stage 1 (Layout Clustering): {stage1_time:.2f}s")
    print(f"Stage 2 (Deep Extraction):   {stage2_time:.2f}s")
    print(f"TOTAL:                       {total_time:.2f}s")
    print("Target:                      < 16.0s")
    print(f"{'=' * 60}\n")

    assert total_time < 16.0, (
        f"Performance target FAILED: {total_time:.2f}s > 16.0s "
        f"(Stage 1: {stage1_time:.2f}s, Stage 2: {stage2_time:.2f}s)"
    )

    # Verify 100 pages are accounted for
    total_pages = sum(c["page_count"] for c in clusters)
    assert total_pages == 100, f"Expected 100 pages in clusters, got {total_pages}"
