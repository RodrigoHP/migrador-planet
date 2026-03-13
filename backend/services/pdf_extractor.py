from pathlib import Path
from typing import List

import pdfplumber

from models.text_block import TextBlock


class PDFExtractor:
    def extract(self, pdf_path: Path) -> List[TextBlock]:
        blocks: List[TextBlock] = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    pw = page.width or 1
                    ph = page.height or 1

                    # Extrair palavras com atributos de fonte
                    words = page.extract_words(extra_attrs=["fontname", "size"])
                    for w in words:
                        blocks.append(
                            TextBlock(
                                text=w["text"],
                                x=w["x0"] / pw,
                                y=w["top"] / ph,
                                width=(w["x1"] - w["x0"]) / pw,
                                height=(w["bottom"] - w["top"]) / ph,
                                page=page_num,
                                font_size=float(w.get("size") or 0),
                                font_name=str(w.get("fontname") or ""),
                                block_type="text",
                            )
                        )

                    # Extrair tabelas
                    tables = page.extract_tables()
                    for table in tables:
                        text = "\n".join(
                            " | ".join(cell or "" for cell in row)
                            for row in table
                            if row
                        )
                        if text.strip():
                            blocks.append(
                                TextBlock(
                                    text=text,
                                    x=0.0,
                                    y=0.0,
                                    width=1.0,
                                    height=0.1,
                                    page=page_num,
                                    block_type="table",
                                )
                            )
        except Exception as exc:
            raise ValueError(f"Erro ao extrair PDF: {exc}") from exc

        return blocks
