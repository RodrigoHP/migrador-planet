# Editor Canvas Specification

## Purpose
The Canvas is the visual workspace where the operator edits document templates.

It renders **real HTML output**, not wireframes.

## Rendering Model

template.json
↓
HTML generator
↓
HTML + CSS
↓
Canvas iframe

## Why iframe

- CSS isolation
- Layout stability
- Accurate preview

## Canvas Responsibilities

- Render template HTML
- Allow element selection
- Support dragging and resizing
- Show real page layout

## Element Identification

Each rendered element includes:

data-template-id

Example:

<span data-template-id="client_name"></span>

This allows the editor to map DOM elements back to template.json.

## Canvas Layout

Toolbar
Structure Tree | Canvas
Inspector