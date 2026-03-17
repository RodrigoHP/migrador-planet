
# Document AI Platform
# Frontend + Processing Pipeline Integrated Architecture

Purpose of this document:
Provide a clear view of how the **Frontend Template Editor** interacts with the **Document Processing Pipeline**.

This document is intended for implementation by engineers or AI coding agents (e.g., Claude Code).

It explains:

- Full pipeline stages
- Frontend interaction points
- Data exchanged between frontend and backend
- Processing flow
- UX behavior tied to pipeline stages

---

# 1. System Overview

The platform converts:

PlanetPress PDF documents

into

HTML + CSS templates with Knockout bindings.

The system consists of two main parts:

1) Document Processing Pipeline (backend)
2) Template Authoring Interface (frontend)

---

# 2. High Level Architecture

User Upload
↓
Document Processing Pipeline
↓
Template Model Generation
↓
Frontend Template Editor
↓
Human Review & Adjustments
↓
Final Template Save

---

# 3. Frontend Responsibilities

The frontend provides the interface for:

- uploading documents
- reviewing detected layout
- adjusting fields and tables
- configuring loops
- testing data
- validating templates

Main pages:

Dashboard
Create Template
Template Editor
Template Preview

---

# 4. Pipeline Stages

The pipeline processes uploaded PDFs before opening the editor.

Stages:

1. PDF Upload
2. Multi Document Analyzer
3. Page Sampling
4. OCR / Text Extraction
5. Anchor Detection
6. Layout Skeleton Builder
7. Field Detection
8. Table Detection
9. Section Detection
10. Nested Section Detection
11. Conditional Block Detection
12. Format Detection
13. Vision Assist
14. Template Model Builder
15. HTML Template Generator
16. CSS Layout Generator
17. Knockout Binding Generator
18. Template Validation
19. Template Preview Generation
20. Editor Preparation
21. Template Review
22. Template Save
23. Template Versioning

---

# 5. Stage Details

## Stage 1 – PDF Upload

User uploads:

- example PDFs
- XSD schema

Frontend screen:

Create Template

Data sent to backend:

PDF files
Schema file

---

## Stage 2 – Multi Document Analyzer

The system analyzes multiple PDFs to identify:

- common layout structure
- repeated elements
- structural anchors

Purpose:

Improve detection accuracy.

---

## Stage 3 – Page Sampling

If documents contain hundreds or thousands of pages, the system selects representative pages.

Example:

Page 1 → Cover  
Page 3 → Table start  
Page 450 → Table middle  
Page 900 → Table end  

These pages are sent to the editor.

---

## Stage 4 – Text Extraction

Text and bounding boxes are extracted.

Libraries may include:

PyMuPDF
OCR engines if needed.

Output:

Structured text blocks with coordinates.

---

## Stage 5 – Anchor Detection

Stable text labels are detected.

Examples:

Cliente  
CPF  
Data  

Anchors serve as layout references.

---

## Stage 6 – Layout Skeleton Builder

Creates a structural representation of the document layout.

Elements:

text blocks
tables
sections
headers
footers

Output:

Layout skeleton model.

---

## Stage 7 – Field Detection

Fields are mapped to schema attributes.

Example:

Cliente → cliente

Confidence score is assigned.

---

## Stage 8 – Table Detection

Tables are identified.

Example:

Data | Descrição | Valor

Mapped to:

collection structure.

---

## Stage 9 – Section Detection

Logical sections are detected.

Example:

Address block
Payment summary

---

## Stage 10 – Nested Section Detection

Nested loops are detected.

Example:

Pedidos
  Itens

---

## Stage 11 – Conditional Block Detection

Sections that appear conditionally are detected.

Example:

Discount section only appears if discount exists.

---

## Stage 12 – Format Detection

Field formatting patterns are inferred.

Examples:

Currency  
CPF  
Date  

---

## Stage 13 – Vision Assist

Vision models analyze complex layouts where heuristic detection fails.

Used for:

tables
complex sections
irregular layouts

---

## Stage 14 – Template Model Builder

A structured template model is created.

Example:

{
 field: "cliente",
 anchor: "Cliente",
 offset: 30
}

---

## Stage 15 – HTML Template Generator

The system generates the base HTML structure.

---

## Stage 16 – CSS Layout Generator

CSS is created for layout positioning and pagination.

---

## Stage 17 – Knockout Binding Generator

Bindings are inserted.

Example:

data-bind="text: cliente"

---

## Stage 18 – Template Validation

Automatic checks:

missing fields
invalid loops
unmapped anchors

---

## Stage 19 – Template Preview Generation

Preview HTML is generated for the editor.

---

## Stage 20 – Editor Preparation

The backend prepares data for the frontend editor.

Returned objects:

layout model
field list
table structures
preview HTML

---

# 6. Frontend Editor Interaction

When the editor loads, it receives:

layout skeleton
field mappings
table mappings
preview HTML

The editor then renders:

PDF Viewer
Layout Overlay
Field Navigator
Table Inspector

---

# 7. Editor Workflow

User actions:

Review fields
Adjust mappings
Configure loops
Set formatting
Test data

Tools available:

Field Review
Bulk Mapping
Loop Boundary Visualization
Grid Alignment
Template Coverage Indicator

---

# 8. Data Playground

Users can simulate input data.

Example:

{
  "cliente": "Maria",
  "movimentos": []
}

Preview updates automatically.

---

# 9. Template Preview

The preview panel renders the generated HTML.

Supports:

pagination
header/footer
dynamic lists

---

# 10. Save Template

The final template includes:

template.html
styles.css
template_model.json

Templates are versioned.

---

# 11. Final System Flow

User uploads PDFs
↓
Pipeline analyzes layout
↓
Template model generated
↓
Frontend editor loads template
↓
User reviews and adjusts
↓
Preview generated
↓
Template saved

---

# 12. Summary

The system integrates:

Document AI pipeline
Human-in-the-loop template editor
Dynamic template generation

The frontend provides the control layer where operators refine the automatically generated template.
