
# Advanced Layout Intelligence — Font Detection, Column/Grid Detection, and Smart Layout Anchors

This document describes three advanced capabilities of the Document Template Editor:

1. Automatic Font Detection
2. Automatic Column / Grid Detection
3. Smart Layout Anchors

These features reduce manual work when converting PDFs into editable templates.

---

# 1. Automatic Font Detection

## Purpose

When a PDF is analyzed, the system extracts font information directly from the document.

Detected properties include:

- Font family
- Font size
- Font weight (bold, regular)
- Text color
- Character spacing
- Line spacing

This ensures that the generated template preserves the visual style of the original document.

---

## Example Detection

Example extracted text block:

Text: "Cliente"

Detected font metadata:

Font Family: Helvetica  
Font Size: 12  
Weight: Bold  
Color: #000000

---

## Interface Wireframe

Font settings appear automatically in the inspector panel.

Font Inspector

Font Family: Helvetica  
Font Size: 12 px  
Font Weight: Bold  
Color: #000000  

[Upload Font]

---

## Missing Font Handling

If the detected font is not available locally:

Detected Font: Univers

Fallback Font: Helvetica

The user can upload:

- TTF
- OTF

Uploaded fonts become part of the template assets.

---

## Pipeline

Font extraction occurs during the **Document Analyzer stage**.

Typical libraries used:

PyMuPDF  
pdfminer

Output example:

font_family  
font_size  
font_weight

These values are mapped to CSS during template generation.

---

# 2. Automatic Column / Grid Detection

## Purpose

Many documents contain aligned columns such as:

Description | Value

Automatic column detection identifies vertical alignment patterns.

---

## Detection Example

PDF content:

Product           Price
Coffee            10
Milk              5

Detected columns:

Column 1 → X = 80px  
Column 2 → X = 450px

---

## Editor Wireframe

The editor overlays column guides.

+-----------------------------------------+
| Product           | Price               |
| Coffee            | 10                  |
| Milk              | 5                   |
+-----------------------------------------+

Vertical guides appear in the editor to help alignment.

---

## Column Panel

Detected Columns

Column 1  
X Position: 80 px

Column 2  
X Position: 450 px

[Lock Columns]

Locked columns become snap targets for elements.

---

## Pipeline

Column detection is performed in the **Layout Engine**.

Methods used:

- vertical alignment clustering
- bounding box comparison
- spacing analysis

This creates a structural grid used by the editor.

---

# 3. Smart Layout Anchors

## Purpose

Layout anchors ensure elements maintain correct positioning during pagination.

Without anchors, elements may shift incorrectly when content grows.

---

## Example Problem

Document layout:

Header  
Table  
Subtotal  
Signature

If the table grows, the signature might move unexpectedly.

Anchors solve this.

---

## Anchor Types

Top Anchor

Elements remain fixed at the top.

Example:

Logo  
Customer name

---

Flow Anchor

Elements follow content flow.

Example:

Tables  
Paragraphs

---

Bottom Anchor

Elements remain at the bottom of each page.

Example:

Signatures  
Totals

---

## Anchor Wireframe

+--------------------------------------+
| HEADER (Top Anchor)                  |
+--------------------------------------+
| FLOW AREA                            |
| Table rows                           |
| Table rows                           |
+--------------------------------------+
| FOOTER (Bottom Anchor)               |
+--------------------------------------+

---

## Inspector Configuration

Anchor Type

(•) Top  
( ) Flow  
( ) Bottom  

Additional rules:

Keep With Previous  
Keep With Next  
Block Together

---

## Pipeline

Anchors are applied during the **Template Builder stage**.

Steps:

1. Detect layout regions
2. Classify blocks
3. Assign anchor behavior
4. Generate pagination rules

---

# Summary

These three systems work together:

Font Detection  
→ preserves visual style

Column Detection  
→ reconstructs document structure

Layout Anchors  
→ guarantee correct pagination

Together they enable accurate conversion of static PDFs into dynamic templates.
