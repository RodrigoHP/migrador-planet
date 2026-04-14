
# Template Editor — Main Screen Detailed Specification

This document describes in detail the **Template Editor**, the central interface of the
Document Template Platform. The editor allows users to transform a detected PDF layout
into a reusable **HTML + CSS + Knockout template**.

The editor supports:

- multi-document analysis
- layout visualization
- field mapping
- table detection
- chart mapping
- optional fields
- conditional sections
- template preview
- human-in-the-loop correction

---

# 1. Overall Layout

The Template Editor layout is divided into five main regions.

```
+--------------------------------------------------------------------------------------+
| Top Toolbar                                                                         |
+--------------------------------------------------------------------------------------+

+----------------------+------------------------------------------------+-------------+
| Field Navigator      |             PDF Viewer + Overlay               | Inspector   |
| (Left Panel)         |                                                | (Right)     |
+----------------------+------------------------------------------------+-------------+

+--------------------------------------------------------------------------------------+
| Multi‑Document Analyzer                                                             |
+--------------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------------+
| Bottom Panel (Data Playground / Example Docs / Console)                             |
+--------------------------------------------------------------------------------------+
```

---

# 2. Top Toolbar

The top toolbar contains global actions for the template.

```
Template: Extrato_Conta | Confidence: 91% | Version: v1.2

[ Coverage Mode ]
[ Diff Mode ]
[ Auto Fix Layout ]
[ Preview ]
[ Save Template ]
[ Export HTML ]
```

## Toolbar Functions

### Coverage Mode

Highlights mapping status:

- 🟩 mapped
- 🟥 missing
- 🟨 detected but not mapped

### Diff Mode

Activates **multi-document layout comparison**.

Allows visual comparison between example PDFs.

### Auto Fix Layout

Automatically fixes:

- spacing problems
- grid alignment
- font inconsistencies
- column alignment

### Preview

Renders template using test data.

### Save Template

Stores:

- HTML template
- CSS layout
- Knockout bindings
- assets
- metadata

### Export HTML

Exports final template package.

---

# 3. Field Navigator (Left Panel)

The Field Navigator lists all elements detected by the pipeline.

```
FIELDS
├ cliente
├ cpf
├ telefone
├ valorTotal
├ endereco

TABLES
├ movimentos
├ pagamentos

CHARTS
├ vendasMensais

ASSETS
├ logoEmpresa
├ assinatura
```

## Interactions

Click → highlight element in PDF

Drag → assign element to template

Hover → preview location in PDF

---

# 4. PDF Viewer + Overlay (Center)

Displays the original PDF with detected layout overlays.

Example:

```
Cliente: João
CPF: 123456789

------------------------------------------
DATA | DESCRIÇÃO | VALOR
------------------------------------------
01/01 | Compra A | 100
02/01 | Compra B | 200

[ CHART AREA ]
```

## Overlay Color Codes

| Color | Meaning |
|------|--------|
| 🟦 | text block |
| 🟩 | mapped field |
| 🟥 | unmapped element |
| 🟨 | detected element |
| 🟪 | table |
| 🟧 | chart |

## Interactions

Click → open Inspector

Drag → reposition

Resize → adjust bounding box

Right click menu:

```
Map field
Convert to table
Mark as static text
Remove element
```

---

# 5. Inspector Panel (Right Side)

Shows properties of the selected element.

## Field Inspector

```
Field Name: cliente

Binding:
data-bind="text: cliente"

Format: string

Alignment: left

Font:
Roboto 12px

Grid Position:
column: 1
row: 2
```

## Table Inspector

```
Table: movimentos

Loop:
foreach: movimentos

Columns:
data
descricao
valor

Header: enabled

Pagination: automatic
```

## Chart Inspector

```
Chart Type: bar
Library: Chart.js

Binding:
labels: meses
values: vendas

Size:
width: 300
height: 200
```

## Asset Inspector

```
Asset: logo.png

Replace image
Remove image
Download asset
```

---

# 6. Multi‑Document Analyzer

This section compares multiple example PDFs.

Example:

```
Example Documents

Doc1.pdf  ✔ base layout
Doc2.pdf  ✔ variation
Doc3.pdf  ✔ variation
Doc4.pdf  ✔ variation
```

## Variation Matrix

```
Field        Doc1  Doc2  Doc3  Doc4
cliente       ✔     ✔     ✔     ✔
cpf           ✔     ✔     ✔     ✔
telefone      ✖     ✔     ✖     ✔
valorTotal    ✔     ✔     ✔     ✔
```

Detected outcomes:

- optional fields
- conditional sections
- layout shifts

Example conditional binding:

```
<!-- ko if: telefone -->
<span data-bind="text: telefone"></span>
<!-- /ko -->
```

---

# 7. Diff Mode

Diff mode allows visual comparison between documents.

```
Doc1 vs Doc2
```

Elements are highlighted:

- 🟩 identical
- 🟨 position difference
- 🟥 missing

Example:

```
Telefone: ---        (Doc1)
Telefone: 999999999  (Doc2)
```

Result: optional field detected.

---

# 8. Bottom Panel

The bottom panel contains testing and debugging tools.

## Data Playground

Used to test template bindings.

Example:

```
{
 "cliente":"João",
 "cpf":"123456789",
 "valorTotal":1200
}
```

Button:

```
Apply Data
```

## Example Document Switcher

```
Doc1.pdf
Doc2.pdf
Doc3.pdf
Doc4.pdf
```

Switching documents updates:

- viewer
- overlays
- field mapping

## Console / Warnings

Displays detected issues.

Example:

```
⚠ Field telefone not mapped
⚠ Table header inconsistent
⚠ Chart data source missing
```

---

# 9. Coverage Mode

Displays mapping coverage.

Example:

```
Coverage Score: 92%

cliente        🟩
cpf            🟩
telefone       🟥
valorTotal     🟩
endereco       🟥
```

Button:

```
Highlight Missing Fields
```

---

# 10. User Workflow

Typical workflow inside the editor:

```
1 open editor
2 enable coverage mode
3 review missing fields
4 compare documents using diff mode
5 apply auto fix
6 adjust layout manually
7 test with sample data
8 preview template
9 save template
```

---

# 11. Frontend Component Tree

Suggested component structure:

```
TemplateEditor
 ├ TopToolbar
 ├ FieldNavigator
 ├ PDFViewer
 │   ├ OverlayLayer
 │   ├ ElementHighlights
 │   └ SelectionTool
 ├ InspectorPanel
 │   ├ FieldInspector
 │   ├ TableInspector
 │   ├ ChartInspector
 │   └ AssetInspector
 ├ MultiDocumentAnalyzer
 └ BottomPanel
     ├ DataPlayground
     ├ ExampleSwitcher
     └ ConsolePanel
```

---

# 12. Editor States

Possible UI states:

- loading
- analyzing
- editing
- reviewing
- preview
- saved

---

# Final Result

A validated template should have:

```
Confidence Score > 90%
Coverage Score > 95%
```

Resulting template output:

- HTML
- CSS
- Knockout bindings
- assets
