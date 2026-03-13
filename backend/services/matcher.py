import re
import unicodedata
import uuid
from typing import Dict, List, Optional

from models.field_mapping import FieldMapping
from models.text_block import TextBlock


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Remove accents, lowercase, collapse separators to single space."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-_\s]+", " ", ascii_str).strip().lower()


# ---------------------------------------------------------------------------
# Levenshtein distance (no external deps)
# ---------------------------------------------------------------------------

def levenshtein_similarity(a: str, b: str) -> float:
    """Return a similarity score in [0, 1] based on Levenshtein distance."""
    if a == b:
        return 1.0
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0.0
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
    return 1.0 - dp[n] / max(m, n)


# ---------------------------------------------------------------------------
# BR format normalisation
# ---------------------------------------------------------------------------

def normalize_br_format(value: str, field_type: str) -> str:
    """Convert common Brazilian formatted values to a normalised string."""
    stripped = value.strip()

    # Currency: R$ 1.234,56 → "1234.56"
    currency_pattern = re.compile(r"R?\$?\s*([\d.]+),(\d{2})")
    m = currency_pattern.search(stripped)
    if m:
        integer_part = m.group(1).replace(".", "")
        decimal_part = m.group(2)
        try:
            return str(float(f"{integer_part}.{decimal_part}"))
        except ValueError:
            pass

    # Date DD/MM/YYYY → YYYY-MM-DD
    date_pattern = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
    m = date_pattern.match(stripped)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # CEP XXXXX-XXX (keep as-is)
    cep_pattern = re.compile(r"^\d{5}-\d{3}$")
    if cep_pattern.match(stripped):
        return stripped

    # Phone: keep only digits
    phone_pattern = re.compile(r"^[\d\s()\-+]+$")
    if phone_pattern.match(stripped) and len(re.sub(r"\D", "", stripped)) >= 8:
        return re.sub(r"\D", "", stripped)

    return stripped


# ---------------------------------------------------------------------------
# Type and confidence mapping helpers
# ---------------------------------------------------------------------------

def _map_xsd_type(xsd_type: str) -> str:
    """Map XSD type string to frontend type enum value."""
    t = xsd_type.lower()
    if t in ("date", "datetime", "time"):
        return "date"
    if t in ("decimal", "float", "double", "integer", "int", "long", "currency"):
        return "currency"
    if t in ("list", "array"):
        return "list"
    return "text"


def _map_confidence(raw: float) -> str:
    """Map numeric confidence [0,1] to frontend string enum."""
    if raw >= 0.8:
        return "high"
    if raw >= 0.5:
        return "medium"
    return "low"


def _map_status(raw_confidence: float, missing_in_data: bool, missing_in_xsd: bool) -> str:
    """Map matching results to frontend status enum."""
    if missing_in_xsd:
        return "optional"
    if missing_in_data:
        return "not_found"
    if raw_confidence >= 0.8:
        return "ok"
    if raw_confidence >= 0.5:
        return "ambiguous"
    return "not_found"


# ---------------------------------------------------------------------------
# Matcher class
# ---------------------------------------------------------------------------

class Matcher:
    """Match PDF TextBlocks against XSD field definitions and data values."""

    def match(
        self,
        blocks: List[TextBlock],
        xsd_fields: List[Dict],
        data_fields: Dict[str, str],
    ) -> List[FieldMapping]:
        """Produce a FieldMapping list from extracted blocks, XSD schema, and data.

        Strategy (per XSD field):
          1. Exact match against normalised block text → confidence 1.0
          2. Levenshtein similarity → proportional confidence
          3. Partial containment → confidence 0.75
        """
        mappings: List[FieldMapping] = []

        # Pre-compute normalised versions of block texts
        norm_blocks = [(normalize_name(b.text), b) for b in blocks if b.text.strip()]

        # Normalised data_fields keys for key-existence checks
        norm_data: Dict[str, str] = {
            normalize_name(k): v for k, v in data_fields.items()
        }

        # Pre-compute normalised XSD names for cross-validation
        xsd_norm_names = {normalize_name(f.get("name", "")) for f in xsd_fields}

        for xsd_field in xsd_fields:
            xsd_name: str = xsd_field.get("name", "")
            xsd_type: str = xsd_field.get("type", "string")
            norm_xsd = normalize_name(xsd_name)

            # --- Find best matching block ---
            best_confidence = 0.0
            best_pdf_value = ""
            best_page_ref: Optional[int] = None
            best_bbox: Optional[Dict[str, float]] = None

            for norm_text, block in norm_blocks:
                # Exact match
                if norm_text == norm_xsd:
                    confidence = 1.0
                else:
                    lev = levenshtein_similarity(norm_text, norm_xsd)
                    # Partial containment boost
                    if (norm_xsd in norm_text or norm_text in norm_xsd) and lev < 0.75:
                        lev = 0.75
                    confidence = lev

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_pdf_value = block.text
                    best_page_ref = getattr(block, "page", None)
                    best_bbox = {
                        "x": block.x,
                        "y": block.y,
                        "width": getattr(block, "width", 0.0),
                        "height": getattr(block, "height", 0.0),
                    }

            # --- Lookup data value (check key existence, not empty value) ---
            missing_in_data = bool(data_fields) and (norm_xsd not in norm_data)
            data_value = norm_data.get(norm_xsd, "")

            # --- Normalise value ---
            normalised = normalize_br_format(best_pdf_value, xsd_type) if best_pdf_value else ""

            mappings.append(
                FieldMapping(
                    id=str(uuid.uuid4()),
                    pdfText=best_pdf_value,
                    jsonPath=xsd_name,
                    type=_map_xsd_type(xsd_type),
                    confidence=_map_confidence(best_confidence),
                    status=_map_status(best_confidence, missing_in_data, False),
                    isManual=False,
                    pageRef=best_page_ref,
                    boundingBox=best_bbox if best_pdf_value else None,
                    raw_confidence=round(best_confidence, 4),
                    data_value=data_value,
                    xsd_type=xsd_type,
                    normalized_value=normalised,
                )
            )

        # --- Detect fields present in data but not in XSD → mark as optional ---
        for data_key, data_val in data_fields.items():
            norm_key = normalize_name(data_key)
            if norm_key not in xsd_norm_names:
                mappings.append(
                    FieldMapping(
                        id=str(uuid.uuid4()),
                        pdfText="",
                        jsonPath=data_key,
                        type="text",
                        confidence="low",
                        status="optional",
                        isManual=False,
                        raw_confidence=0.0,
                        data_value=data_val,
                        xsd_type="string",
                        normalized_value="",
                    )
                )

        return mappings
