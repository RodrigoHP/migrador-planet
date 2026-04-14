"""Stage 3 — Detecção de Seções Repetidas (Story 48.4).

Implementa detect_repeated_sections(): dado uma lista de blocos de texto de
uma página, identifica grupos de N≥2 blocos com estrutura similar (fingerprint)
em posições y progressivas e os marca como RepeatedSection.

Algoritmo de fingerprint:
  - x0_bucket  = round(x0 / tolerance_x)
  - width_bucket = round(width / tolerance_w)
  - n_words_bucket = round(n_words / 3) * 3

Grupos com N≥min_occurrences onde y_span > avg_height*(N-1)*0.5 são seções
repetidas (i.e., lista de itens estruturalmente idênticos).
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

from models.pipeline_context import (
    RepeatedSection,
    SectionFieldTemplate,
    SectionInstance,
    SectionTemplate,
)

logger = logging.getLogger(__name__)

_DEFAULT_TOLERANCE_X = 10.0  # pt — tolerância de x0 para agrupar blocos
_DEFAULT_TOLERANCE_W = 15.0  # pt — tolerância de largura
_DEFAULT_MIN_OCCURRENCES = 2  # mínimo de instâncias para ser lista


def _block_fingerprint(
    block: dict[str, Any],
    tolerance_x: float,
    tolerance_w: float,
) -> tuple[int, int, int]:
    """Retorna fingerprint estrutural de um bloco: (x0_bucket, width_bucket, n_words_bucket)."""
    bbox = block.get("bbox", [0, 0, 0, 0])
    if len(bbox) < 4:
        return (0, 0, 0)
    x0 = bbox[0]
    x1 = bbox[2]
    width = x1 - x0
    text = block.get("text", "")
    n_words = len(text.split()) if text.strip() else 0

    x0_bucket = round(x0 / max(tolerance_x, 1.0))
    w_bucket = round(width / max(tolerance_w, 1.0))
    n_words_bucket = round(n_words / 3) * 3

    return (x0_bucket, w_bucket, n_words_bucket)


def detect_repeated_sections(
    blocks: list[dict[str, Any]],
    page_index: int = 0,
    tolerance_x: float = _DEFAULT_TOLERANCE_X,
    tolerance_w: float = _DEFAULT_TOLERANCE_W,
    min_occurrences: int = _DEFAULT_MIN_OCCURRENCES,
) -> list[RepeatedSection]:
    """Detecta grupos de blocos repetidos em uma página.

    Parameters
    ----------
    blocks:
        Lista de blocos de texto da página (dicts com 'bbox', 'text', opcionalmente 'id').
    page_index:
        Índice da página (usado para o modelo RepeatedSection.page_index).
    tolerance_x, tolerance_w:
        Tolerâncias em pontos para o bucketing de posição X e largura.
    min_occurrences:
        Mínimo de instâncias para considerar um grupo como seção repetida.

    Returns
    -------
    list[RepeatedSection]:
        Seções repetidas detectadas. Blocos participantes são referenciados
        em SectionInstance.block_ids para que o tree_builder possa excluí-los
        do processamento normal.
    """
    if not blocks:
        return []

    # Agrupa blocos por fingerprint
    fp_groups: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        fp = _block_fingerprint(block, tolerance_x, tolerance_w)
        if fp == (0, 0, 0):
            continue
        fp_groups[fp].append(block)

    repeated: list[RepeatedSection] = []

    for fp, group in fp_groups.items():
        if len(group) < min_occurrences:
            continue

        # Ordenar por y0 crescente
        group_sorted = sorted(group, key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])

        # Verificar que estão em posições y progressivas (não sobrepostos)
        y_positions = [b.get("bbox", [0, 0, 0, 0])[1] for b in group_sorted]
        avg_height = sum(b.get("bbox", [0, 0, 0, 0])[3] - b.get("bbox", [0, 0, 0, 0])[1] for b in group_sorted) / len(
            group_sorted
        )

        y_span = max(y_positions) - min(y_positions)
        min_span = avg_height * (len(group_sorted) - 1) * 0.5

        if y_span < min_span:
            # Blocos muito próximos uns dos outros — provavelmente não é lista
            continue

        # Construir instâncias
        instances: list[SectionInstance] = []
        for b in group_sorted:
            bbox = list(b.get("bbox", [0, 0, 0, 0]))
            text = b.get("text", "")
            block_id = b.get("id", "")
            instances.append(
                SectionInstance(
                    bbox=bbox,
                    texts=[text] if text else [],
                    block_ids=[block_id] if block_id else [],
                )
            )

        # Construir item_template: analisa textos para detectar dynamic vs static
        texts_by_position = [inst.texts[0] if inst.texts else "" for inst in instances]
        unique_texts = set(texts_by_position)
        field_type = "dynamic" if len(unique_texts) > 1 else "static"
        static_value = texts_by_position[0] if field_type == "static" and texts_by_position else None

        template = SectionTemplate(
            fields=[
                SectionFieldTemplate(
                    name=f"field_{fp[0]}_{fp[1]}",
                    field_type=field_type,
                    value=static_value,
                )
            ]
        )

        # Bbox envelope (bounding box de todas as instâncias)
        all_bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in group_sorted]
        x0_env = min(bb[0] for bb in all_bboxes)
        y0_env = min(bb[1] for bb in all_bboxes)
        x1_env = max(bb[2] for bb in all_bboxes)
        y1_env = max(bb[3] for bb in all_bboxes)
        bbox_envelope = [x0_env, y0_env, x1_env, y1_env]

        section_id = f"repeated_{str(uuid.uuid4())[:8]}"

        repeated.append(
            RepeatedSection(
                section_id=section_id,
                list_item_count=len(instances),
                item_template=template,
                instances=instances,
                page_index=page_index,
                bbox_envelope=bbox_envelope,
            )
        )

    if repeated:
        logger.debug(
            "Página %d: %d seção(ões) repetida(s) detectada(s) com %s instâncias",
            page_index,
            len(repeated),
            [r.list_item_count for r in repeated],
        )

    return repeated


def collect_repeated_block_ids(repeated_sections: list[RepeatedSection]) -> set[str]:
    """Retorna o conjunto de block_ids que fazem parte de alguma RepeatedSection.

    Usado pelo tree_builder para evitar double-counting de blocos.
    """
    ids: set[str] = set()
    for rs in repeated_sections:
        for inst in rs.instances:
            ids.update(bid for bid in inst.block_ids if bid)
    return ids
