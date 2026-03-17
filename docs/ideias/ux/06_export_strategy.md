# Export Strategy

Two export types exist.

## 1. Template Export (for editing)

template.zip

Contents:

template.json
schema.json
assets/
fonts/

Used to reopen templates inside the editor.

## 2. Final Template Export

document_template.zip

Contents:

index.html
styles.css
assets/
fonts/

Used by external systems.

## Rendering Flow

data
↓
Knockout bindings applied
↓
HTML rendered
↓
PDF engine converts HTML → PDF