"""pytest configuration and session-scoped fixtures for backend test suite.

Session-scoped fixtures build shared PDFs once per test session instead of
once per test function. This reduces I/O overhead when many tests use the
same PDF content. (Story 45.2)

Fixture naming:
  session_simple_pdf_path     — 2-page generic test PDF (pipeline orchestrator tests)
  session_boleto_pdf_path     — 2-page boleto-style PDF (e2e tests)
  session_simple1p_pdf_path   — 1-page generic PDF (screenshot/upload tests)
"""

from __future__ import annotations

import os

import fitz  # PyMuPDF
import pytest

# ---------------------------------------------------------------------------
# Auth disabled (Story 15.3)
# ---------------------------------------------------------------------------

os.environ.setdefault("AUTH_DISABLED", "true")


# ---------------------------------------------------------------------------
# Session-scoped PDF fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def session_simple_pdf_path(tmp_path_factory):
    """2-page simple test PDF used by pipeline orchestrator tests.

    Equivalent to _create_test_pdf(path, num_pages=2) — built once per session.
    """
    tmp = tmp_path_factory.mktemp("shared_pdfs")
    path = str(tmp / "simple_test.pdf")
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 120), f"Test content page {i + 1}", fontsize=12)
        page.insert_text((50, 200), "Some body text for the page here", fontsize=10)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="session")
def session_boleto_pdf_path(tmp_path_factory):
    """2-page boleto-style PDF used by e2e pipeline tests.

    Equivalent to _create_boleto_pdf(path) — built once per session.
    """
    tmp = tmp_path_factory.mktemp("shared_pdfs")
    path = str(tmp / "boleto_test.pdf")
    doc = fitz.open()

    # Page 1 — boleto content
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 40), "Banco Bradesco S.A.", fontname="helv", fontsize=14)
    page.insert_text((400, 40), "BOLETO", fontname="helv", fontsize=16)
    page.insert_text((50, 120), "Nome:", fontname="helv", fontsize=10)
    page.insert_text((120, 120), "Joao da Silva Santos", fontname="helv", fontsize=10)
    page.insert_text((50, 150), "CPF:", fontname="helv", fontsize=10)
    page.insert_text((120, 150), "123.456.789-10", fontname="helv", fontsize=10)
    page.insert_text((50, 200), "Vencimento:", fontname="helv", fontsize=10)
    page.insert_text((150, 200), "10/04/2026", fontname="helv", fontsize=10)
    page.insert_text((50, 250), "Valor:", fontname="helv", fontsize=10)
    page.insert_text((120, 250), "R$ 1000,00", fontname="helv", fontsize=10)
    page.insert_text((50, 300), "Referente a servicos prestados conforme contrato vigente", fontname="helv", fontsize=9)
    page.insert_text((50, 350), "Nosso Numero:", fontname="helv", fontsize=10)
    page.insert_text((170, 350), "900000", fontname="helv", fontsize=10)
    page.draw_line((50, 80), (545, 80), color=(0, 0, 0), width=1)
    page.draw_rect(fitz.Rect(40, 400, 555, 500), color=(0, 0, 0), width=0.5)

    # Page 2 — identical layout, different data (same cluster)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 40), "Banco Bradesco S.A.", fontname="helv", fontsize=14)
    page2.insert_text((400, 40), "BOLETO", fontname="helv", fontsize=16)
    page2.insert_text((50, 120), "Nome:", fontname="helv", fontsize=10)
    page2.insert_text((120, 120), "Maria Oliveira", fontname="helv", fontsize=10)
    page2.insert_text((50, 150), "CPF:", fontname="helv", fontsize=10)
    page2.insert_text((120, 150), "987.654.321-00", fontname="helv", fontsize=10)
    page2.insert_text((50, 200), "Vencimento:", fontname="helv", fontsize=10)
    page2.insert_text((150, 200), "15/05/2026", fontname="helv", fontsize=10)
    page2.insert_text((50, 250), "Valor:", fontname="helv", fontsize=10)
    page2.insert_text((120, 250), "R$ 2500,00", fontname="helv", fontsize=10)
    page2.insert_text(
        (50, 300), "Referente a servicos prestados conforme contrato vigente", fontname="helv", fontsize=9
    )
    page2.insert_text((50, 350), "Nosso Numero:", fontname="helv", fontsize=10)
    page2.insert_text((170, 350), "900001", fontname="helv", fontsize=10)
    page2.draw_line((50, 80), (545, 80), color=(0, 0, 0), width=1)
    page2.draw_rect(fitz.Rect(40, 400, 555, 500), color=(0, 0, 0), width=0.5)

    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="session")
def session_simple1p_pdf_path(tmp_path_factory):
    """1-page simple PDF used by screenshot/upload tests in stage2.

    Equivalent to _create_simple_pdf(path, num_pages=1) — built once per session.
    """
    tmp = tmp_path_factory.mktemp("shared_pdfs")
    path = str(tmp / "simple1p_test.pdf")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "Test document", fontsize=12)
    page.insert_text((50, 200), "Some body text for the test page", fontsize=10)
    page.insert_text((50, 300), "Additional content line", fontsize=10)
    doc.save(path)
    doc.close()
    return path
