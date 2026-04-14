
# DOCUMENT_AI_PLATFORM_MASTER_ARCHITECTURE.md
## PlanetPress PDF → Dynamic HTML Template Platform
### Complete Architecture & Design Specification

---

# 1. Purpose

This document defines the **complete architecture for a system that converts static PlanetPress PDFs into reusable HTML templates** capable of generating dynamic documents.

The goal is that **a developer or an AI coding system (such as Claude Code)** can read this document and implement the full platform.

The document explains:

• the problem domain  
• architectural decisions  
• processing pipeline  
• services and responsibilities  
• libraries and why they were chosen  
• AI strategy  
• template engine design  
• human‑in‑the‑loop workflow  
• infrastructure and scaling  

---

# 2. Problem Domain

PlanetPress produces **static PDFs**.

These PDFs contain:

• layout  
• typography  
• visual alignment  
• tables  

But they **do not contain semantic information**.

Example PDF content:

Cliente: João Silva  
CPF: 123.456.789‑00  
Saldo: R$ 1.234,56  

The system must infer:

| Label | Value | Schema Field |
|------|------|--------------|
Cliente | João Silva | cliente |
CPF | 123.456.789‑00 | documento |
Saldo | R$ 1.234,56 | valor |

This requires **document understanding**, not simple text extraction.

---

# 3. System Goal

Convert:

PDF + XSD schema

Into:

Reusable HTML Template

Example template:

```html
<p>Cliente: {{cliente}}</p>
<p>CPF: {{formatCpf(documento)}}</p>

<table>
{% for item in movimentacoes %}
<tr>
<td>{{item.data}}</td>
<td>{{item.descricao}}</td>
<td>{{item.valor | currency}}</td>
</tr>
{% endfor %}
</table>
```

Later the template receives JSON data and produces the final PDF.

---

# 4. Architectural Philosophy

The platform follows several principles.

## Layout‑First Processing

Never convert:

PDF → HTML

Instead convert:

PDF → Layout Model → HTML Template

This allows consistent understanding of structure.

## Hybrid Intelligence

The system combines:

• deterministic layout analysis  
• machine learning  
• vision models  
• human validation  

## Continuous Learning

Operator corrections are stored and used to improve the system.

---

# 5. High‑Level Architecture

Major subsystems:

1. Document Ingestion
2. Document Parsing
3. Layout Analysis
4. Semantic Understanding
5. Template Generation
6. Human Review Interface
7. Rendering Engine
8. Learning Engine

---

# 6. Processing Pipeline

Complete pipeline:

1 Upload PDF  
2 Parse PDF structure  
3 Cluster pages by layout  
4 Detect layout regions  
5 Interpret layout with vision models  
6 Build layout model  
7 Infer data formats  
8 Map labels to schema fields  
9 Compute confidence score  
10 Human review (if necessary)  
11 Generate HTML template  
12 Store template  
13 Render PDF using template  

---

# 7. Document Ingestion

Responsibilities:

• receive uploaded PDF  
• receive XSD schema  
• store document  
• create processing job  

Technology:

Python + FastAPI

Why:

• async APIs  
• strong ecosystem  
• automatic documentation  

Example API:

POST /documents

---

# 8. PDF Parsing

Library:

PyMuPDF

Why:

• extremely fast
• accurate bounding boxes
• access to fonts and layout geometry

Example output:

{
"text": "Cliente",
"bbox": [100,200,200,220],
"font_size": 12
}

---

# 9. Page Clustering

Large PDFs may contain hundreds of identical pages.

Example:

Page 1 → cover  
Pages 2‑900 → statements  

Processing every page is wasteful.

Solution:

Cluster pages using layout features.

Libraries:

scikit‑learn  
NumPy  

Algorithm:

K‑Means clustering on layout vectors.

---

# 10. Layout Segmentation

Purpose:

Detect structural regions in a page.

Regions:

• header  
• body  
• tables  
• footer  

Libraries:

LayoutParser  
OpenCV  

Reason:

LayoutParser includes pretrained document layout models.

---

# 11. Vision Understanding

Vision models help interpret relationships between elements.

Example:

Label → Cliente  
Value → João Silva

Primary model:

GPT‑4o Vision

Alternative models:

LayoutLMv3  
Donut  
Pix2Struct  

Vision is used only when deterministic logic cannot determine relationships.

---

# 12. Layout Model

All extracted information becomes a structured layout model.

Example:

{
 "pages":[
  {
   "sections":[
    {
     "type":"header",
     "elements":[
      {"label":"Cliente","binding":"cliente"}
     ]
    }
   ]
  }
 ]
}

This model drives template generation.

---

# 13. Format Inference

The system must detect data formatting automatically.

Examples:

123.456.789‑00 → CPF  
01/02/2024 → Date  
R$ 1.234,56 → Currency  

Libraries:

regex  
dateparser  

---

# 14. Semantic Field Matching

Different documents may use different labels.

Examples:

CPF  
Documento  
Doc  

All map to canonical field:

documento

Libraries:

SentenceTransformers  
pgvector  

---

# 15. Human‑in‑the‑Loop Review

Operators validate results.

Frontend stack:

Vue.js

Libraries:

PDF.js  
Konva.js  
Monaco Editor  

Capabilities:

• select region in PDF  
• map schema field  
• edit template  
• preview rendering  

---

# 16. Template Engine

Template engine:

Jinja2

Reasons:

• mature ecosystem  
• Python integration  
• loops and filters  

---

# 17. Rendering Engine

Rendering system:

Puppeteer

Pipeline:

HTML template + JSON data → render HTML → generate PDF

Supports:

• multi‑page tables  
• headers / footers  
• pagination  

---

# 18. Database

Database:

PostgreSQL

Extension:

pgvector

Tables:

documents  
templates  
layout_models  
layout_embeddings  
semantic_fields  
format_patterns  
human_feedback  

---

# 19. Learning System

The system improves using feedback.

Sources:

• human corrections  
• layout similarity  
• semantic corrections  
• format detection  

Libraries:

PyTorch  
HuggingFace Transformers  

---

# 20. Infrastructure

Containers:

Docker

Orchestration:

Kubernetes

Queues:

RabbitMQ  
Kafka  
Redis Queue  

Workers:

PDF parsing worker  
Vision worker  
Template generation worker  
Rendering worker  

---

# 21. Repository Structure

document‑ai‑platform/

backend/  
frontend/  
ai_engine/  
infra/  
shared/  
docs/

---

# 22. Final Capabilities

Once trained, the platform can:

• detect document layouts automatically  
• identify fields and tables  
• infer formatting  
• reuse templates for similar documents  
• generate HTML templates automatically  

---

# End of Document
