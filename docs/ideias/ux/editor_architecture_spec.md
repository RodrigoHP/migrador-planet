
# Editor Architecture Specification
## Visual Editor + Code Editor + Canvas Synchronization

Project: PlanetPress → HTML/Knockout Template Migrator
Module: Template Editor
Purpose: Define how the editor works, including Visual editing, Code editing, Canvas rendering,
and synchronization rules between structure and HTML.

---

# 1. Editor Philosophy

The editor has two modes:

Visual Mode
Code Mode

Both modes manipulate the same underlying **Template Structure Model**.

The system must guarantee:

- visual editing remains stable
- code editing remains possible
- both remain synchronized

The source of truth is always:

Template Structure JSON

Never the HTML.

---

# 2. Core Editor Components

The editor is composed of 4 main parts:

Structure Tree
Canvas Renderer
Inspector Panels
Code Editor

Layout:

Toolbar
---------------------------------------
Structure | Canvas | Inspector
---------------------------------------
Diagnostics / Data Testing / Console

---

# 3. Template Structure (Source of Truth)

All templates are represented internally as JSON.

Example:

{
  "type": "header",
  "children": [
    {
      "type": "text",
      "binding": "cliente.nome"
    }
  ]
}

This structure defines:

layout hierarchy
data bindings
components
sections

The HTML is generated from this structure.

---

# 4. HTML Generation

Pipeline:

Template Structure
↓
HTML Generator
↓
Canvas Renderer

Example generated HTML:

<div class="header">
  <span data-bind="text: cliente.nome"></span>
</div>

The HTML is not edited directly in visual mode.

---

# 5. Canvas Renderer

The Canvas shows the **live preview of the generated HTML template**.

Important:

The Canvas does NOT show the original PDF.
The Canvas shows the generated HTML layout.

Canvas responsibilities:

render template preview
simulate pagination
allow element selection
highlight structure nodes

---

# 6. Pagination Simulation

Documents produced by the template are paginated.

The Canvas must simulate real pages.

Example:

PAGE 1
-----------------
Header
Content
Footer

PAGE 2
-----------------
Header
Content
Footer

Page structure:

<div class="page">
    <header></header>
    <flow></flow>
    <footer></footer>
</div>

---

# 7. Header and Footer Behavior

Header and footer repeat on every page.

Header settings:

height
padding
background
repeat per page

Footer settings:

height
padding
page numbering

---

# 8. Flow Content

The Flow area contains dynamic content:

tables
text
charts
lists

Flow grows vertically.

When flow exceeds available space:

automatic page break occurs.

---

# 9. Element Selection in Canvas

The Canvas allows selecting elements.

Clicking an element:

Canvas element
↓
template node id
↓
Structure Tree selection
↓
Inspector opens

Bidirectional sync:

Tree selection highlights canvas element
Canvas selection selects tree node

---

# 10. Hierarchical Selection

Elements may exist inside nested structures.

Example:

Table
 Row
  Cell
   Text

When clicking inside the canvas, the system resolves hierarchy.

Example popup:

Select Element

Text
Cell
Row
Table

---

# 11. Inspector Panels

Inspector panels allow editing properties.

Levels:

Page
Section
Component
Element

Properties include:

spacing
alignment
fonts
visibility rules
data binding
pagination rules

---

# 12. Code Editor

The Code Editor allows advanced editing of the generated HTML template.

Used for:

complex bindings
conditional logic
advanced layout tweaks

Example:

<span data-bind="visible: telefone"></span>

---

# 13. Code Editor Synchronization

Important rule:

Structure JSON remains the source of truth.

Editing flow:

Visual Mode:

Structure
↓
HTML Generator
↓
Canvas

Code Mode:

HTML edit
↓
HTML Parser
↓
Structure Update
↓
Canvas render

---

# 14. Validation Layer

When saving edits from the Code Editor the system validates:

HTML syntax
Knockout bindings
template structure integrity

If validation fails:

changes are rejected
error is displayed

---

# 15. PDF Reference View

The editor includes a PDF reference tab.

Canvas Tabs:

Canvas HTML
PDF Reference

PDF Reference is rendered using PDF.js.

Purpose:

compare layout
inspect original document
verify alignment

---

# 16. Coverage Mode

Coverage mode highlights mapping completeness.

Green = mapped
Red = unmapped

Helps operator detect missing bindings.

---

# 17. Diff Mode

Diff mode compares:

PDF detected layout
Template structure

Used to identify structural mismatches.

---

# 18. Performance Considerations

Large documents may contain hundreds of pages.

Canvas must limit rendering:

render first N pages
simulate additional pages

Recommended:

max preview pages = 5

---

# 19. Zoom Controls

Canvas supports zoom.

Controls:

Zoom Out (-)
100%
Zoom In (+)

Zoom affects display only.

---

# 20. Future Enhancements

Potential improvements:

AI layout corrections
smart pagination optimization
visual diff with PDF
component libraries

---

END OF SPECIFICATION
