# Document Template Engine — Architecture Overview

## Purpose
This system converts static PDFs (PlanetPress generated) into dynamic HTML templates.
These templates can then be used by external systems to generate final PDFs.

The platform focuses on:

- Template extraction
- Visual editing
- HTML template generation
- Pagination control
- Export of reusable document templates

The system **does not generate PDFs directly**.

Instead:

data → HTML render → external PDF engine → PDF

## Pipeline Overview

PlanetPress PDF
↓
Vision + Layout Detection
↓
Layout Skeleton
↓
Template Generator
↓
Visual Editor
↓
Export HTML Template
↓
External System Applies Data
↓
PDF Engine Converts HTML → PDF

## Key Architectural Principles

1. HTML is the source of rendering truth.
2. Pagination must be controlled by the HTML template.
3. Editor must reflect real HTML rendering.
4. PDF engines should act only as converters.
5. Layout must support dynamic data growth.