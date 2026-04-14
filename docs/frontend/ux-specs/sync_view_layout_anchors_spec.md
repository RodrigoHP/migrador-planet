
# Sync View & Layout Anchors Specification
Project: PlanetPress → HTML/Knockout Template Migrator
Module: Editor UI Enhancements

This document consolidates the discussions about **Sync View** and **Layout Anchors**,
including their purpose, behavior, UI placement, and interaction with the editor pipeline.

---

# 1. Sync View Overview

Sync View is an editor mode that allows the operator to see the **Canvas preview and the original PDF side by side**.

Purpose:

- compare the generated template with the original document
- verify alignment
- detect layout mismatches
- validate field mappings

---

# 2. Sync View Activation

Sync View is enabled from the editor toolbar.

Example toolbar:

Canvas | PDF | HTML | Code | 🔗 Sync

When activated, the central panel switches from tabs to a **split view layout**.

---

# 3. Split View Layout

Example layout:

----------------------------------------------------
| Canvas (Generated Template) | PDF (Reference) |
----------------------------------------------------
| Header                      | Header           |
| Cliente: {{nome}}           | Cliente: João    |
| CPF: {{cpf}}                | CPF: 123...      |
| Table                       | Table            |
| Row 1                       | Row 1            |
| Row 2                       | Row 2            |
----------------------------------------------------

The operator can visually compare both sides.

---

# 4. Scroll Synchronization

When Sync View is active:

Scrolling one panel scrolls the other.

Example:

Canvas scroll
↓
PDF scroll follows

This keeps both layouts aligned.

---

# 5. Highlight Synchronization

When selecting an element in Canvas:

Canvas highlight
↓
Matching bounding box highlighted in PDF.

This uses coordinates detected by the Vision stage.

---

# 6. Coverage Mode Integration

Coverage Mode highlights mapping completeness.

Canvas:

Green → mapped fields
Red → unmapped fields

PDF:

Bounding boxes detected by AI.

Sync View allows the operator to visually identify missing mappings.

---

# 7. Layout Anchors Concept

Layout Anchors are reference points used to align template elements with the original PDF layout.

Anchors are derived from:

text blocks
logos
table headers
repeated patterns

---

# 8. Anchor Detection

Anchors are detected during pipeline analysis stages.

Example anchors:

Document title
Section headers
Table column headers
Logos

These anchors serve as structural reference points.

---

# 9. Anchor Usage in Editor

Anchors help:

align template elements
guide element placement
assist automatic layout reconstruction

Example:

PDF:
Client Name: João

Template:
Client Name: {{cliente.nome}}

Anchor = "Client Name"

---

# 10. Anchors in Sync View

When Sync View is active:

Anchors can be displayed as markers on both Canvas and PDF.

Example:

Canvas:
[Anchor: Client Name]

PDF:
[Anchor: Client Name]

This visually connects template structure to the original layout.

---

# 11. Multiple Layout Types

Documents may contain multiple layouts.

Example:

Page 1 → Cover
Page 2-200 → Transactions
Page 201 → Summary

The editor detects Layout Types and allows switching between them.

Example selector:

Layout: [ Transactions ▼ ]

Sync View updates accordingly.

---

# 12. Representative Page Strategy

For large documents, the editor does not render every page.

Instead:

One representative page per layout type is shown.

Example:

Layout: Transactions
Representative Page: 32

---

# 13. Sync View Performance

Large PDFs can contain hundreds of pages.

Performance strategy:

render representative pages only
lazy-load PDF pages
limit canvas preview pages

---

# 14. User Workflow Example

Operator workflow:

1 Upload documents
2 Pipeline detects layouts
3 Editor opens
4 Operator selects layout type
5 Activates Sync View
6 Adjusts template layout
7 Validates alignment with PDF

---

# 15. Benefits

Sync View improves:

layout accuracy
mapping validation
operator confidence
debugging speed

Layout Anchors improve:

automatic reconstruction
layout stability
alignment with source documents

---

END OF SPECIFICATION
