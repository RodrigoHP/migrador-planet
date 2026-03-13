from pathlib import Path
from typing import Dict, List

from lxml import etree


# XSD namespace prefix
XS = "http://www.w3.org/2001/XMLSchema"


class XSDParser:
    def parse(self, xsd_path: Path) -> List[Dict]:
        """Parse an XSD file and return a list of field descriptors.

        Each descriptor contains:
            name        - element name
            type        - xs:type value (e.g. xs:string, xs:date)
            min_occurs  - minOccurs attribute (default "1")
            max_occurs  - maxOccurs attribute (default "1")
            description - xs:documentation content (if present)
        """
        try:
            # Secure parser: disable XXE (external entities, DTD, network access)
            parser = etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
            )
            tree = etree.parse(str(xsd_path), parser)
        except Exception as exc:
            raise ValueError(f"Erro ao parsear XSD: {exc}") from exc

        root = tree.getroot()
        fields: List[Dict] = []

        for element in root.iter(f"{{{XS}}}element"):
            name = element.get("name")
            if not name:
                continue

            field_type = element.get("type", "xs:string")
            # Strip namespace prefix if fully qualified
            if "}" in field_type:
                field_type = field_type.split("}")[-1]

            min_occurs = element.get("minOccurs", "1")
            max_occurs = element.get("maxOccurs", "1")

            # Extract xs:documentation from xs:annotation/xs:documentation
            description = ""
            annotation = element.find(f"{{{XS}}}annotation")
            if annotation is not None:
                doc = annotation.find(f"{{{XS}}}documentation")
                if doc is not None and doc.text:
                    description = doc.text.strip()

            fields.append(
                {
                    "name": name,
                    "type": field_type,
                    "min_occurs": min_occurs,
                    "max_occurs": max_occurs,
                    "description": description,
                }
            )

        return fields
