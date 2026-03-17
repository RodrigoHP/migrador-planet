
# DOCUMENT AI PLATFORM – PIPELINE COMPLEMENT (23 STAGES)

This document complements the main architecture specification.

Its purpose is to **clearly define the canonical 23-stage processing pipeline**
for the Document AI platform that converts PlanetPress-generated PDFs
into reusable HTML templates.

Claude should use this document together with the main architecture document
to correctly understand:

• the exact pipeline order
• the logical grouping of stages
• the dependency between stages
• the architectural reasoning

---------------------------------------------------------------------
# OVERVIEW

The system transforms:

PDF + XSD
↓
Document Understanding
↓
Layout Intelligence
↓
Vision Interpretation
↓
Template Generation

---------------------------------------------------------------------
# PIPELINE ORGANIZATION

The 23 stages are organized into **8 logical blocks**.

1. Document Acquisition
2. Layout Discovery
3. Layout Intelligence
4. Table Intelligence
5. Layout Semantics
6. Vision Interpretation
7. Data Mapping
8. Validation + Template Generation

---------------------------------------------------------------------
# BLOCK 1 — DOCUMENT ACQUISITION

## 1. Upload PDFs + XSD
Receives example PDFs and the schema describing data structure.

## 2. PDF Parsing
Extracts raw content from PDFs including:
• text blocks
• coordinates
• fonts
• page boundaries

Recommended library:
PyMuPDF

---------------------------------------------------------------------
# BLOCK 2 — LAYOUT DISCOVERY

## 3. Layout Skeleton Builder
Creates a structural skeleton representing document geometry.

Extracts:
• text blocks
• bounding boxes
• table candidates
• layout zones

## 4. Page Layout Clustering
Groups pages with similar layouts.

Purpose:
Reduce large PDFs to a small set of layout types.

## 5. Representative Page Selection
Selects representative pages from each cluster for further analysis.

## 6. Layout Fingerprint Generation
Creates a structural signature for the layout.

Example:
{
 tableCount:1,
 columnCount:3,
 headerBlocks:4
}

## 7. Layout Registry Lookup
Checks if a template already exists for the detected layout.

---------------------------------------------------------------------
# BLOCK 3 — LAYOUT INTELLIGENCE

## 8. Layout Alignment
Aligns coordinates across multiple example PDFs.

Purpose:
Normalize small layout differences.

## 9. Multi‑Example Layout Analysis
Compares multiple documents to detect:

• labels
• dynamic values
• repeated patterns

Example:

PDF A
Cliente: João

PDF B
Cliente: Maria

Inference:

Cliente → label
value → dynamic field

## 10. Layout Stability Analysis
Classifies layout blocks:

STABLE
VARIABLE
OPTIONAL

Example:

Cliente → stable
CPF → stable
Aviso atraso → optional

## 11. Variant Detection
Detects conditional blocks appearing only in some documents.

Example:

if saldo < 0
show warning

## 12. Structural Layout Normalization
Converts raw PDF layout into logical zones:

HEADER
BODY
TABLE
FOOTER

---------------------------------------------------------------------
# BLOCK 4 — TABLE INTELLIGENCE

## 13. Table Identity Detection
Detects tables and assigns identifiers.

Example:

transactions table
fees table

## 14. Table Continuation Detection
Detects tables that span multiple pages.

Signals used:

• repeated headers
• aligned columns
• repeating row patterns

IMPORTANT DESIGN RULE

Tables must be detected BEFORE anchor detection.

Otherwise table headers such as:

Data | Descrição | Valor

may be incorrectly interpreted as fields.

---------------------------------------------------------------------
# BLOCK 5 — LAYOUT SEMANTICS

## 15. Layout Zone Detection
Identifies major zones:

HEADER
BODY
FOOTER

## 16. Anchor Detection
Detects textual anchors (labels) used to map fields.

Examples:

Cliente
CPF
Data
Valor

---------------------------------------------------------------------
# BLOCK 6 — VISION INTERPRETATION

## 17. Vision Analysis
Uses a Vision model to interpret semantic meaning of the document.

The Vision model analyzes:

• labels
• values
• table semantics
• document context

Recommended model:
OpenAI Vision

## 18. Vision Self‑Check
Validates Vision output for consistency.

Checks include:

• label-value alignment
• field placement
• table structure consistency

If inconsistencies are detected the system may:

• reprocess Vision with additional context
• lower confidence score

---------------------------------------------------------------------
# BLOCK 7 — DATA MAPPING

## 19. Field Intelligence Mapping
Maps detected fields to the XSD schema.

Important design decision:

Schema is used AFTER Vision interpretation.

Pipeline:

Vision → detected fields
↓
Schema mapping

This avoids forcing incorrect mappings.

## 20. Format Detection
Infers formatting rules from observed values.

Examples:

12345678900 → CPF
1000.50 → currency
2023-01-01 → date

Generated template may include filters:

{{cpf | cpf}}
{{valor | currency}}

## 21. Confidence Scoring
Each extracted element receives a confidence score.

Rules:

confidence ≥ 0.8 → automatic
0.6–0.8 → optional review
< 0.6 → human review required

---------------------------------------------------------------------
# BLOCK 8 — VALIDATION AND TEMPLATE GENERATION

## 22. Layout Consistency Validation
Ensures that the interpreted structure is consistent with
the previously detected layout skeleton.

## 23. Template Generation
Generates the final HTML template with bindings.

Example:

Cliente: {{cliente}}

{% for item in documentos %}
<tr>
<td>{{item.data}}</td>
<td>{{item.valor}}</td>
</tr>
{% endfor %}

---------------------------------------------------------------------
# POST‑PIPELINE OPERATIONS

The following operations occur after template generation
and are not considered part of the core 23-stage pipeline.

Pagination Rules Injection

Template Optimization

Human Review

Learning Engine

Template Registry

---------------------------------------------------------------------
# IMPLEMENTATION NOTE FOR CLAUDE

The 23 stages represent **logical pipeline steps**, not microservices.

They should be implemented within a small set of modules:

DocumentAnalysisModule
LayoutDiscoveryModule
LayoutIntelligenceModule
TableIntelligenceModule
VisionModule
DataMappingModule
TemplateEngineModule

This approach keeps the architecture modular while avoiding
excessive service fragmentation.

---------------------------------------------------------------------
END OF PIPELINE COMPLEMENT DOCUMENT
