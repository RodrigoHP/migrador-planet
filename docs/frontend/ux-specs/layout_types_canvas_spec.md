
# Layout Types & Canvas Behavior Specification
Project: PlanetPress → HTML/Knockout Template Migrator
Module: Editor Canvas + Layout Types

Purpose:
Define how Layout Types are detected, represented in the UI, and how the Canvas behaves
when editing documents that contain multiple page layouts.

---

# 1. Concept: Layout Types

Large documents often contain repeated page structures.

Example PDF:

Page 1   → Cover
Page 2   → Transactions
Page 3   → Transactions
Page 4   → Transactions
Page 5   → Summary

Detected Layout Types:

- Cover
- Transactions
- Summary

Instead of editing each page individually, the operator edits **one template per Layout Type**.

---

# 2. Layout Type Detection (Pipeline)

During document analysis the system:

1. Extracts page layout structure
2. Compares page geometry
3. Clusters similar layouts

Example result:

285 pages
→ 3 Layout Types

Cluster output:

Layout Type 1 → Cover → pages [1]
Layout Type 2 → Transactions → pages [2–284]
Layout Type 3 → Summary → pages [285]

---

# 3. Layout Type Selector in the Editor

The editor toolbar contains a Layout Type selector.

Wireframe:

------------------------------------------------
Template: Extrato_Bancario
Layout: [ Transactions ▼ ]
Confidence: 91%   Coverage: 93%
------------------------------------------------

Dropdown example:

Transactions
Cover
Summary

Changing the selection updates:

Canvas
PDF Reference
Structure Tree
Inspector

---

# 4. Canvas Behavior with Layout Types

The Canvas **never renders all pages of the document**.

Instead it renders a **representative page** of the selected layout.

Example:

Layout: Transactions
Representative Page: 32

Canvas shows:

┌──────── PAGE (Transactions) ────────┐
│ Header                              │
│                                     │
│ Date | Description | Value          │
│ 01/01 | Purchase A | 100            │
│ 02/01 | Purchase B | 200            │
│ 03/01 | Purchase C | 300            │
│                                     │
│ Footer                              │
└─────────────────────────────────────┘

---

# 5. Canvas + Pagination Simulation

The Canvas simulates pagination using sample data.

Example preview:

PAGE 1
┌─────────────────────────┐
│ Header                  │
│ Table                   │
│ Row 1                   │
│ Row 2                   │
│ Row 3                   │
│ Footer                  │
└─────────────────────────┘

PAGE 2
┌─────────────────────────┐
│ Header                  │
│ Row 4                   │
│ Row 5                   │
│ Row 6                   │
│ Footer                  │
└─────────────────────────┘

Pagination is dynamic based on content height.

---

# 6. Canvas Tabs

The central editor panel contains multiple tabs.

Wireframe:

-----------------------------------------------------
| Canvas | PDF | HTML | Code |
-----------------------------------------------------

Descriptions:

Canvas → rendered template preview
PDF → original document reference
HTML → generated template HTML (read-only)
Code → editable HTML/CSS

---

# 7. Sync View Mode

Sync View allows Canvas and PDF to be shown side-by-side.

Wireframe:

--------------------------------------------------------------
| Canvas (Template Preview) | PDF Reference |
--------------------------------------------------------------
| Header                    | Header        |
| Cliente: {{nome}}         | Cliente: João |
| CPF: {{cpf}}              | CPF: 123...   |
| Table                     | Table         |
| Row 1                     | Row 1         |
--------------------------------------------------------------

Scroll and highlight are synchronized.

---

# 8. Canvas Interaction Model

Operators interact with elements visually.

Supported actions:

- Click to select
- Highlight corresponding structure node
- Inspector opens automatically

Hierarchy example:

Table
 Row
  Cell
   Text

Popup selection example:

Select Element:

Text
Cell
Row
Table

---

# 9. Structure Tree Relationship

The structure tree reflects the template structure.

Example:

Document
 ├ Header
 │ ├ Logo
 │ ├ Client Name
 │ └ CPF
 ├ Flow
 │ └ Transactions Table
 └ Footer
   └ Page Number

Selecting a node highlights the corresponding element in the Canvas.

---

# 10. Performance Strategy

Large documents must not render all pages.

Strategy:

Render representative pages only
Limit preview pages to 5
Lazy load PDF pages

---

# 11. Example User Workflow

1 Upload multiple PDFs
2 Pipeline detects layout clusters
3 Editor opens with default layout selected
4 Operator edits template
5 Switch layout type using dropdown
6 Validate alignment with Sync View
7 Export template

---

# 12. Visual Summary

Editor Layout:

┌──────────────────────────────────────────────────────┐
│ Toolbar                                              │
│ Template | Layout Selector | Confidence | Coverage   │
├──────────────┬───────────────────────────┬───────────┤
│ Structure    │ Canvas / PDF / HTML / Code│ Inspector │
│ Tree         │                           │           │
├──────────────┴───────────────────────────┴───────────┤
│ Multi‑Document Analyzer / Diagnostics                │
└──────────────────────────────────────────────────────┘

---

END OF SPECIFICATION
