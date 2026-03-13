import json
from pathlib import Path
from typing import Any, Dict

from lxml import etree


class DataParser:
    def parse(self, data_path: Path) -> Dict[str, str]:
        """Detect file format and return a flat {field: value} dict.

        JSON objects are flattened with dot-notation keys (parent.child).
        XML elements are extracted as {tag: text} pairs.
        """
        raw = data_path.read_text(encoding="utf-8").strip()

        if self._is_json(raw):
            return self._parse_json(raw)
        else:
            return self._parse_xml(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_json(self, raw: str) -> bool:
        """Return True if the content looks like JSON."""
        return raw.startswith("{") or raw.startswith("[")

    def _parse_json(self, raw: str) -> Dict[str, str]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Erro ao parsear JSON: {exc}") from exc
        result: Dict[str, str] = {}
        self._flatten(data, "", result)
        return result

    def _flatten(self, obj: Any, prefix: str, result: Dict[str, str]) -> None:
        """Recursively flatten a JSON object into dot-notation keys."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                self._flatten(value, full_key, result)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                full_key = f"{prefix}.{i}" if prefix else str(i)
                self._flatten(item, full_key, result)
        else:
            result[prefix] = str(obj) if obj is not None else ""

    def _parse_xml(self, raw: str) -> Dict[str, str]:
        try:
            # Secure parser: disable XXE (external entities, DTD, network access)
            parser = etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
            )
            root = etree.fromstring(raw.encode("utf-8"), parser)
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Erro ao parsear XML: {exc}") from exc

        result: Dict[str, str] = {}
        for element in root.iter():
            # Strip namespace from tag
            tag = element.tag
            if "}" in tag:
                tag = tag.split("}")[-1]
            text = (element.text or "").strip()
            if text:
                # If duplicate tag names exist, last value wins
                result[tag] = text
        return result
