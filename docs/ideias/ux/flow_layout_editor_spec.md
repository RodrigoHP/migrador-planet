
# Document Template Editor — Flow Layout & Smart Flow Specification

This document describes the complete behavior of the Template Editor when working with paginated documents,
especially documents where tables grow and automatically continue onto the next page.

Typical examples:

- bank statements
- invoices with many rows
- transaction reports
- financial statements

The editor solves this using a Flow Layout model.

---

# 1. Core Concept — Flow Layout

Instead of editing static pages, the user edits a logical page structure composed of sections.

Structure:

HEADER
CONTENT FLOW AREA
FOOTER

Example:

+-----------------------------------------------------+
| HEADER                                              |
| Cliente: João                                       |
| CPF: 123456                                         |
+-----------------------------------------------------+

+-----------------------------------------------------+
| CONTENT FLOW AREA                                   |
| Movimento                      Valor                |
| Compra A                       100                  |
| Compra B                       200                  |
| Compra C                       300                  |
+-----------------------------------------------------+

+-----------------------------------------------------+
| FOOTER                                              |
| Página 1                                            |
+-----------------------------------------------------+

The CONTENT FLOW AREA expands automatically and creates new pages when needed.

---

# 2. Editor Layout

+----------------------------------------------------------------------------------+
| Template: Extrato_Conta | Layout: Transaction Page | Detected pages: 200        |
|----------------------------------------------------------------------------------|
| [Snap ON] [Coverage Mode] [Diff Mode] [Flow Preview] [Preview PDF] [Save]       |
+----------------------+--------------------------------+--------------------------+
| Field Navigator      | Flow Page Editor                | Inspector                |
| Fields               | HEADER                          | Element: Table           |
| Tables               | CONTENT FLOW                    | Data Source: movimentos  |
| Charts               | FOOTER                          | Pagination: enabled      |
+----------------------+--------------------------------+--------------------------+

---

# 3. Flow Page Editor

The center of the editor shows a representative page.

+-------------------------------------------------------------+
| HEADER (repeats on every page)                              |
+-------------------------------------------------------------+

+-------------------------------------------------------------+
| CONTENT FLOW AREA                                           |
| Movimento                      Valor                        |
| Compra mercado                 100                          |
| Compra farmácia                200                          |
| Compra gasolina                150                          |
| ---------------- PAGE BREAK PREVIEW ----------------        |
+-------------------------------------------------------------+

+-------------------------------------------------------------+
| FOOTER (repeats on every page)                              |
+-------------------------------------------------------------+

---

# 4. Flow Table

Primary dynamic element:

movimentos

Configuration:

Table Settings
Data Source: movimentos
Allow page break: true
Repeat header: true
Minimum rows per page: 3

---

# 5. Automatic Pagination

Example:

Rows per page = 20

If dataset contains 100 rows:

Page 1 → rows 1–20
Page 2 → rows 21–40
Page 3 → rows 41–60
Page 4 → rows 61–80
Page 5 → rows 81–100

Header and footer repeat automatically.

---

# 6. Page Break Preview

Flow Preview mode displays predicted page breaks:

----- PAGE BREAK -----

This helps users verify pagination before rendering.

---

# 7. Data Playground

Example JSON:

{
 "cliente": "João",
 "movimentos": [
  {"descricao":"Compra A","valor":100},
  {"descricao":"Compra B","valor":200}
 ]
}

Increasing the number of rows increases page count automatically.

---

# 8. Representative Page Model

For large PDFs:

Layout detected: Transaction Page
Representative page of 200 pages

User edits a single layout template.

---

# 9. Smart Flow Anchors

Smart Flow Anchors prevent elements from breaking incorrectly across pages.

Common cases:

- subtotals
- totals
- signatures
- notes

Example layout:

Rows
Rows
Subtotal
Signature

---

# 10. Anchor Types

Keep With Previous
Subtotal remains with the preceding rows.

Keep With Next
Section header stays with the following content.

Block Together
Entire block must stay on one page.

---

# 11. Anchor Configuration

Inspector example:

Smart Flow Rules
Keep With Previous: enabled
Minimum rows before break: 3
Keep Block Together: optional

---

# 12. Example Behavior

Without anchors:

Page 1
Row A
Row B

Page 2
Subtotal

With anchors:

Page 1
Row A

Page 2
Row B
Subtotal

---

# 13. Header Behavior

Header repeats automatically on every page.

Header Settings
Repeat each page: enabled

---

# 14. Footer Behavior

Footer repeats automatically on every page.

Footer Settings
Repeat each page: enabled

---

# 15. Layout Tree (Advanced)

Document
 ├ Header
 ├ Flow Section
 │   └ Table movimentos
 └ Footer

---

# 16. Rendering Model

Header
Flow Table
Footer
Automatic Page Break
Repeat

---

# 17. Example Use Case

Transactions: 350 rows
Rows per page: 20

Result:

18 pages generated automatically.

---

# 18. Summary

The editor uses:

Flow Layout
Representative Pages
Automatic Pagination
Smart Flow Anchors

This enables scalable multi-page document generation.
