import uuid
from typing import Any, Dict, List

from models.field_mapping import FieldMapping


class FidelityScorer:
    def score(self, fields: List[FieldMapping]) -> dict:
        """Compute a fidelity score based on high-confidence field mappings.

        Returns a dict with:
            score       - float 0–100
            comment     - human-readable summary string
            suggestions - list matching frontend IASuggestion interface
                          {id, type, message, action}
        """
        if not fields:
            return {"score": 0.0, "comment": "Nenhum campo mapeado.", "suggestions": []}

        high_conf = [f for f in fields if f.confidence == "high"]
        low_conf = [f for f in fields if f.confidence == "low"]
        score = round(len(high_conf) / len(fields) * 100, 1)

        comment = (
            f"{score}% dos campos mapeados com alta confiança. "
            f"{len(fields) - len(high_conf)} campos requerem revisão."
        )

        # IASuggestion shape matches frontend: {id, type, message, action}
        suggestions: List[Dict[str, Any]] = [
            {
                "id": str(uuid.uuid4()),
                "type": "warning",
                "message": (
                    f"Campo '{f.jsonPath}' com baixa confiança de mapeamento "
                    f"(raw: {f.raw_confidence:.2f}). Verificar manualmente."
                ),
                "action": "Revisar mapeamento",
            }
            for f in low_conf
        ]

        return {"score": score, "comment": comment, "suggestions": suggestions}
