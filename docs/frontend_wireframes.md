
# Document Template Migration Platform
# Full Frontend UX Flow & Screen Wireframes

This document complements the frontend architecture specification and focuses on:

- Full user journey
- Screen wireframes
- UI behavior
- Navigation structure
- Operator workflow

Goal:
Provide a clear blueprint for building the frontend interface.

---

# 1. Application Navigation

Main navigation structure:

Dashboard
Create Template
Templates
Template Editor
Preview

Navigation layout:

+------------------------------------------------+
| Logo | Templates | Create Template | Settings |
+------------------------------------------------+

---

# 2. Screen: Dashboard

Purpose:
Provide overview of existing templates.

Wireframe:

+---------------------------------------------------------------+
| Dashboard                                                     |
+---------------------------------------------------------------+

Templates

+---------------------+------------+-------------+---------------+
| Template Name       | Version    | Last Edit   | Status        |
+---------------------+------------+-------------+---------------+
| Extrato Bancário    | 1.0        | 2026‑03‑14  | Active        |
| Fatura Cartão       | 2.1        | 2026‑03‑10  | Active        |
| Contrato Cliente    | 1.3        | 2026‑03‑01  | Active        |
+---------------------+------------+-------------+---------------+

Actions:
Edit
Duplicate
Delete

---

# 3. Screen: Create Template

Purpose:
Upload PDF examples and schema.

Wireframe:

+---------------------------------------------------------------+
| Create Template                                               |
+---------------------------------------------------------------+

Upload Example PDFs

[ Upload Files ]

Uploaded:

Doc1.pdf
Doc2.pdf
Doc3.pdf

Upload Schema

[ Upload XSD ]

Actions:

[ Start Analysis ]

---

# 4. Screen: Processing

Purpose:
Display pipeline progress.

Wireframe:

Analyzing documents...

✓ Multi‑document analysis
✓ Layout detection
✓ Table detection
✓ Field detection
✓ Template generation

Progress bar shown during processing.

---

# 5. Screen: Template Editor Workspace

Main working interface.

Layout:

+----------------------------------------------------------------------------------+
| Toolbar                                                                         |
| Save | Preview | Validate | Visual Mode | Code Mode                              |
+----------------------------------------------------------------------------------+

Template Coverage: 92%

+--------------------+--------------------+----------------------+
| PDF Viewer         | Layout Overlay     | Field Navigator      |
|                    |                    |                      |
| Cliente: João      | cliente → cliente  | cliente (3)          |
| CPF: 123...        | cpf → cpf          | cpf (2)              |
|                    |                    | valor_total          |
+--------------------+--------------------+----------------------+

+--------------------------------------------------------------+
| Table Inspector                                               |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
| Data Playground                                               |
+--------------------------------------------------------------+

---

# 6. Screen: Field Mapping

Purpose:
Fix incorrect field detection.

Wireframe:

+---------------------------------------------------+
| Field Inspector                                   |
+---------------------------------------------------+

Detected Label: "Cliente"

Map To:

[ cliente v ]

Confidence: High

---

# 7. Screen: Table Inspector

Purpose:
Configure detected tables.

Wireframe:

+--------------------------------------------------+
| Table: movimentos                                |
+--------------------------------------------------+

Columns

data
descricao
valor

Mapping:

data → data
descricao → descricao
valor → valor

---

# 8. Screen: Loop Configuration

Purpose:
Configure repeating sections.

Wireframe:

+------------------------------------------+
| Create Repeating Section                 |
+------------------------------------------+

Collection Name:

movimentos

Loop Start Row: 1
Loop End Row: dynamic

Preview rows displayed.

---

# 9. Screen: Conditional Blocks

Purpose:
Define conditional sections.

Example:

+------------------------------------------+
| Conditional Rule                         |
+------------------------------------------+

Condition:

show if desconto exists

Preview updated instantly.

---

# 10. Screen: Page Layout Settings

Purpose:
Configure page size and margins.

Wireframe:

+------------------------------------------+
| Page Settings                            |
+------------------------------------------+

Page Size:
A4

Orientation:
Portrait

Margins:

Top
Bottom
Left
Right

---

# 11. Screen: Data Playground

Purpose:
Test templates with sample data.

Wireframe:

+--------------------------------------------------------------+
| Data Playground                                              |
+--------------------------------------------------------------+

JSON Data Editor

{
  "cliente": "Maria",
  "movimentos": []
}

Preview updates automatically.

---

# 12. Screen: Template Preview

Purpose:
Display final rendered layout.

Wireframe:

+---------------------------------------------------------------+
| Preview Document                                              |
+---------------------------------------------------------------+

Page 1
Page 2
Page 3

Rendered HTML with Knockout bindings.

---

# 13. Screen: Save Template

Purpose:
Store template in system.

Wireframe:

+----------------------------------------+
| Save Template                          |
+----------------------------------------+

Template Name:

Extrato_Bancario

Version:

1.0

[ Save Template ]

---

# 14. Final UX Workflow

Complete user journey:

Upload PDFs
Upload XSD
Run analysis
Open template editor
Review field mapping
Adjust tables and loops
Configure formatting
Test data
Preview document
Save template

